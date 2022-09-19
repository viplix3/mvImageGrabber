import os
import logging
import json
from datetime import datetime

from mvAcquire.mvDeviceUtils import findActiveDevices


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


if __name__ == "__main__":
    opts = readConfig("../cfg/AppConfig.json")
    recording_dir = getDateTimeRecordingDir(opts)

    os.makedirs(opts["dirs"]["logdir"], exist_ok=True)
    # os.makedirs(recording_dir, exist_ok=True)

    logging.basicConfig(
        level=logging.DEBUG,
        filename=os.path.join(
            opts["dirs"]["logdir"],
            "logs_{}.log".format(datetime.now().strftime("%Y-%m-%d_%H-%M-%S")),
        ),
        filemode="w",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logging.info("Recorded images will be saved at path " + recording_dir)

    findActiveDevices()
