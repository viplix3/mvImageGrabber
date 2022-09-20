import logging
import utils

from mvAcquire import mvDeviceUtils

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    opts = utils.readConfig("../cfg/AppConfig.json")
    recordingDir, logDir = utils.setupDirs(opts)
    utils.setupLogging(logDir)

    logger.info("Recorded images will be saved at path " + recordingDir)

    mvDeviceUtils.findActiveDevices()
    mvDeviceUtils.initCamera(opts["camera"]["family"], opts["camera"]["config"])

    # TODO: Implement this function to initialize MQTT pub/sub
    # initPubSub()

    mvDeviceUtils.initRecording(recordingDir)
