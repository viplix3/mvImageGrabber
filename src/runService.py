import logging
import utils

from mvAcquire import mvDeviceUtils

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    opts = utils.readConfig("../cfg/AppConfig.json")
    recordingDir, logDir = utils.setupDirs(opts)
    utils.setupLogging()

    logger.info("Recorded images will be saved at path " + recordingDir)

    mvDeviceUtils.findActiveDevices()

    # TODO: Add code to find camera of given family and initialize it
    mvDeviceUtils.initCamera(opts["camera"]["family"])

    # TODO: Implement this function
    # mvDeviceUtils.loadDeviceSettingsFromXML(opts["camera"]["config"])
    # initPubSub() # TODO: Implement this function to initialize MQTT pub/sub

    mvDeviceUtils.initRecording(recordingDir)
