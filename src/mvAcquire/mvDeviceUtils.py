import os
import ctypes
import numpy
import logging

from datetime import datetime
from time import sleep
from PIL import Image

from mvIMPACT import acquire


# mvIMPACT.acquire.DeviceManager class instance
# Everytime this instance is created shared libraries are loaded dynamically
# hence defining it in a module
deviceManager = acquire.DeviceManager()
logger = logging.getLogger(__name__)


def supportsValue(prop, value):
    if prop.hasDict:
        validValues = []
        prop.getTranslationDictValues(validValues)
        return value in validValues

    if prop.hasMinValue and prop.getMinValue() > value:
        return False

    if prop.hasMaxValue and prop.getMaxValue() < value:
        return False

    return True


def conditionalSetProperty(prop, value):
    if prop.isValid and prop.isWriteable and supportsValue(prop, value):
        prop.write(value)
        logger.info("Property '%s' set to '%s'." % (prop.name(), prop.readS()))


def getConnectedDeviceInfo():
    connectedDeviceInfo = ""
    for i in range(deviceManager.deviceCount()):
        pDev = deviceManager.getDevice(i)
        currDeviceInfo = ""
        currDeviceInfo = "[" + str(i) + "]: " + pDev.serial.read() \
            + "(" + pDev.product.read() + ", " + pDev.family.read()

        if pDev.interfaceLayout.isValid:
            conditionalSetProperty(
                pDev.interfaceLayout,
                acquire.dilGenICam)
            currDeviceInfo += ", interface layout: " \
                + pDev.interfaceLayout.readS()

        if pDev.acquisitionStartStopBehaviour.isValid:
            conditionalSetProperty(
                pDev.acquisitionStartStopBehaviour,
                acquire.assbUser)
            currDeviceInfo += ", acquisition start/stop behaviour: " \
                + pDev.acquisitionStartStopBehaviour.readS()

        if pDev.isInUse:
            currDeviceInfo += ", !!!ALREADY IN USE!!!"
        currDeviceInfo += ")\n"
        connectedDeviceInfo += currDeviceInfo

    return connectedDeviceInfo


def findActiveDevices():
    while deviceManager.deviceCount() == 0:
        logger.warn("No device found")
        sleep(0.5)
        deviceManager.updateDeviceList()
    else:
        logger.info("Found %d device(s)" % deviceManager.deviceCount())
        logger.info(getConnectedDeviceInfo())


def loadDeviceSettings(fInterface, cameraSettingsFile):
    try:
        fInterface.loadSetting(cameraSettingsFile)
    except Exception as e:
        logger.error("Error loading camera settings file: %s" % e)
        logger.error("Continuing without loading settings file")
    else:
        logger.info("Camera settings loaded from file: %s"
                    % cameraSettingsFile)


def initCamera(cameraFamily, cameraSettingsFile):
    cameraObject = deviceManager.getDeviceByFamily(cameraFamily)

    if cameraObject is None:
        logger.error("No camera belonging to family %s found" % cameraFamily)
        logger.info("Re-initializing camera search")
        findActiveDevices()
        initCamera(cameraFamily, cameraSettingsFile)
    else:
        logger.info("Camera (%s) belonging to family (%s) found"
                    % (cameraFamily, cameraObject.product.read()))
        fInterface = acquire.FunctionInterface(cameraObject)
        loadDeviceSettings(fInterface, cameraSettingsFile)
        return cameraObject, fInterface


def convertCapturedBufferToImage(capturedBuffer):
    cbuf = (ctypes.c_char * capturedBuffer.imageSize.read()).from_address(int(capturedBuffer.imageData.read()))
    channelType = numpy.uint16 if capturedBuffer.imageChannelBitDepth.read() > 8 else numpy.uint8
    arr = numpy.fromstring(cbuf, dtype=channelType)

    arr.shape = (capturedBuffer.imageHeight.read(),
                 capturedBuffer.imageWidth.read(),
                 -1)
    arr = arr[:, :, :3] # 4th channel is redundant, we can remove it

    capturedImage = Image.fromarray(arr, 'RGB')
    return capturedImage


def executeAcquisitionProcess(cameraObject,
                              cameraFunctionalInterface,
                              recordingDir,
                              timeout_ms=100):
    logger.info("Starting acquisition")

    statisticsObject = acquire.Statistics(cameraObject)
    pPreviousRequest = None

    while True:
        requestNr = cameraFunctionalInterface.imageRequestWaitFor(timeout_ms)
        if cameraFunctionalInterface.isRequestNrValid(requestNr):
            pRequest = cameraFunctionalInterface.getRequest(requestNr)
            if pRequest.isOK:
                logger.info(cameraObject.serial.read() + ": " + 
                            statisticsObject.framesPerSecond.name() + ": " +
                            statisticsObject.framesPerSecond.readS() + ", " +
                            statisticsObject.errorCount.name() + ": " +
                            statisticsObject.errorCount.readS() + ", " +
                            statisticsObject.captureTime_s.name() + ": " +
                            statisticsObject.captureTime_s.readS())
                capturedImage = convertCapturedBufferToImage(pRequest)
                outImgFileName = "{}.jpg".format(datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
                capturedImage.save(os.path.join(recordingDir, outImgFileName))

                if pPreviousRequest is not None:
                    pPreviousRequest.unlock()
                pPreviousRequest = pRequest
                cameraFunctionalInterface.imageRequestSingle()
        else:
            logger.error("imageRequestWaitFor failed: {}, {}".format(
                         requestNr,
                         acquire.ImpactAcquireException.getErrorCodeAsString(requestNr)))


def initAcquisition(cameraObject, cameraFunctionalInterface):
    while cameraFunctionalInterface.imageRequestSingle() == acquire.DMR_NO_ERROR:
        logger.info("Buffer queued")

    if cameraObject.acquisitionStartStopBehaviour.read() == acquire.assbUser:
        acquisitionInitResult = cameraFunctionalInterface.acquisitionStart()
        if acquisitionInitResult != acquire.DMR_NO_ERROR:
            logger.error("Error initializing acquisition: %s"
                         % acquire.ImpactAcquireException.getErrorCodeAsString(
                            acquisitionInitResult))
        else:
            logger.info("Acquisition initialiation successsful")
    else:
        logger.error("Acquisition not possible due to acquisition property %s"
                     % cameraObject.acquisitionStartStopBehavious.readS())
