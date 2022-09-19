import logging
from time import sleep

from mvIMPACT import acquire


# mvIMPACT.acquire.DeviceManager class instance
# Everytime this instance is created shared libraries are loaded dynamically
# hence defining it in a module
deviceManager = acquire.DeviceManager()
logger = logging.getLogger(__name__)


def getConnectedDeviceInfo():
    connectedDeviceInfo = ""
    for i in range(deviceManager.deviceCount()):
        pDev = deviceManager.getDevice(i)
        currDeviceInfo = ""
        currDeviceInfo = "[" + str(i) + "]: " + pDev.serial.read() \
            + "(" + pDev.product.read() + ", " + pDev.family.read()
        if pDev.acquisitionStartStopBehaviour.isValid:
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
