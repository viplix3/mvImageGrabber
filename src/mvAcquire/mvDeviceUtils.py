import ctypes
import numpy
import logging

from datetime import datetime
from time import sleep

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
    capturedImage = arr[:, :, :3]  # 4th channel is redundant, we can remove it

    return capturedImage


def executeAcquisitionProcess(cameraObject,
                              cameraFunctionalInterface,
                              imageWriter,
                              timeout_ms=100):
    logger.info("Starting acquisition")
    statisticsObject = acquire.Statistics(cameraObject)
    pPreviousRequest = None
    numFramesCaptured = 1
    FPS = []

    while True:
        try:
            requestNr = cameraFunctionalInterface.imageRequestWaitFor(timeout_ms)
            if cameraFunctionalInterface.isRequestNrValid(requestNr):
                pRequest = cameraFunctionalInterface.getRequest(requestNr)
                if pRequest.isOK:
                    numFramesCaptured += 1
                    FPS.append(float(statisticsObject.framesPerSecond.readS()))
                    if numFramesCaptured % 100 == 0:
                        avgFPS = numpy.average(FPS)
                        # FPS = []
                        logMsg = "Captured %d frames " % numFramesCaptured
                        logMsg += cameraObject.serial.read() + ": "
                        logMsg += "Average" + statisticsObject.framesPerSecond.name() + ": "
                        logMsg += str(avgFPS) + ", "
                        logMsg += statisticsObject.errorCount.name() + ": "
                        logMsg += statisticsObject.errorCount.readS() + ", "
                        logMsg += statisticsObject.captureTime_s.name() + ": "
                        logMsg += statisticsObject.captureTime_s.readS()
                        logger.info(logMsg)

                    capturedImage = convertCapturedBufferToImage(pRequest)
                    imageObj = {}
                    currTimeStamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
                    currDate = currTimeStamp.split("_")[0]
                    currTime = currTimeStamp.split("_")[1]
                    currHour = currTime.split("-")[0]

                    if currDate != imageWriter.currWriteDate or \
                       currHour != imageWriter.currWriteHour:
                        imageWriter.updateWriteDirs(currDate, currHour)

                    imageObj["timestamp"] = "{}_{}".format(currDate, currTime)
                    imageObj["image"] = capturedImage
                    imageWriter.addImageToBuffer(imageObj)

                    if pPreviousRequest is not None:
                        pPreviousRequest.unlock()
                    pPreviousRequest = pRequest
                    cameraFunctionalInterface.imageRequestSingle()
            else:
                logger.error("imageRequestWaitFor failed: {}, {}".format(
                            requestNr,
                            acquire.ImpactAcquireException.getErrorCodeAsString(requestNr)))
        except KeyboardInterrupt:
            logger.warn("KeyboardInterrupt")
            logger.info("Cleaning up")
            imageWriter.stopImageIOThread()
            return


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
