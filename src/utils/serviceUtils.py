import os
import json
from datetime import datetime
import logging


def readConfig(filename):
    with open(filename, "r") as file:
        config = json.load(file)
    return config


def getDateTimeRecordingDir(opts):
    next_hour = str((datetime.now().hour + 1) % 24).zfill(2)
    recording_dir = os.path.join(
        opts["dirs"]["recdir"],
        datetime.now().strftime("%Y-%m-%0d/%H") + "H-" + str(next_hour) + "H",
    )
    return recording_dir


def setupDirs(opts):
    recordingDir = getDateTimeRecordingDir(opts)
    logDir = opts["dirs"]["logdir"]

    os.makedirs(recordingDir, exist_ok=True)
    os.makedirs(logDir, exist_ok=True)

    return recordingDir, logDir


def setupLogging(logDir):
    logging.basicConfig(
        level=logging.DEBUG,
        filename=os.path.join(
            logDir,
            "logs_{}.log".format(datetime.now().strftime("%Y-%m-%d_%H-%M-%S")),
        ),
        filemode="w",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
