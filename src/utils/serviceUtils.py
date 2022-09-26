import os
import json
from datetime import datetime
import logging


def readConfig(filename):
    with open(filename, "r") as file:
        config = json.load(file)
    return config


def setupDirs(opts):
    recordingDir = opts["dirs"]["recdir"]
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
