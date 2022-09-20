import logging
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
            conditionalSetProperty(pDev.interfaceLayout, acquire.dilGenICam)
            currDeviceInfo += ", interface layout: " \
                + pDev.interfaceLayout.readS()

        if pDev.acquisitionStartStopBehaviour.isValid:
            conditionalSetProperty(pDev.acquisitionStartStopBehaviour,
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


def loadDeviceSettings(fInterface, cameraSettingFile):
    try:
        fInterface.loadSetting(cameraSettingFile)
    except Exception as e:
        logger.error("Error loading camera settings file: %s" % e)
        logger.error("Continuing without loading settings file")
    else:
        logger.info("Camera settings loaded from file: %s" % cameraSettingFile)


def initCamera(cameraFamily, cameraSettingsFile):
    cameraObject = deviceManager.getDeviceByFamily(cameraFamily)

    if cameraObject is None:
        logger.error("No camera belonging to family %s found" % cameraFamily)
        logger.info("Re-initializing camera search")
        findActiveDevices()
        initCamera(cameraFamily, cameraSettingsFile)
    else:
        logger.info("Camera belonging to family %s found: %s" % 
                        (cameraFamily, cameraObject.product.read()))
        fInterface = acquire.FunctionInterface(cameraObject)
        loadDeviceSettings(fInterface, cameraSettingsFile)
        return cameraObject
