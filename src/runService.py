import logging
import utils.serviceUtils as serviceUtils
from utils.ioUtils import ImageIO

from mvAcquire import mvDeviceUtils

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    opts = serviceUtils.readConfig("../cfg/AppConfig.json")
    recordingDir, logDir = serviceUtils.setupDirs(opts)
    serviceUtils.setupLogging(logDir)

    logger.info("Recorded images will be saved at path " + recordingDir)

    mvDeviceUtils.findActiveDevices()
    cameraObject, functionalInterface = mvDeviceUtils.initCamera(
        opts["camera"]["family"], opts["camera"]["config"])

    # TODO: Implement this function to initialize MQTT pub/sub
    # initPubSub()

    mvDeviceUtils.initAcquisition(cameraObject, functionalInterface)
    imageWriter = ImageIO(recordingDir)
    imageWriter.startImageIOThread()

    mvDeviceUtils.executeAcquisitionProcess(cameraObject,
                                            functionalInterface,
                                            imageWriter)
    if KeyboardInterrupt:
        logger.info("Cleaning up")
        imageWriter.stopImageIOThread()
