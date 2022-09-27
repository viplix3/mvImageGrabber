import cv2
import os
import threading
import logging

from collections import deque

logger = logging.getLogger(__name__)


class ImageIO:
    def __init__(self, recordingDir, bufferSize=500, writeFreqCount=200):
        self.recordingBaseDir = recordingDir
        self.bufferSize = bufferSize
        self.imageBuffer = deque(maxlen=bufferSize)
        self.writeBufferSize = writeFreqCount

        self.currWriteDate = None
        self.currWriteHour = None

        self.exitEvent = threading.Event()
        self.imageBufferLock = threading.Lock()
        self.threadCondition = threading.Condition()
        self.imageIOThread = threading.Thread(target=self.imageIOThreadFunc)

    def startImageIOThread(self):
        logger.info("Starting image IO thread")

        try:
            if not self.imageIOThread.is_alive():
                self.imageIOThread.start()
            logger.info("Image IO thread started successfully")
        except RuntimeError:
            logger.error("Error starting image IO thread")

    def stopImageIOThread(self):
        logger.info("Stopping immage IO thread")

        with self.threadCondition:
            logger.info("Dumping images in queue")
            while len(self.imageBuffer) > 0:
                imageData = self.imageBuffer.popleft()
                self.dumpImageToDisk(imageData)

            self.exitEvent.set()
            self.threadCondition.notify()
        self.imageBuffer.clear()
        self.imageIOThread.join()

    def imageIOThreadFunc(self):
        while not self.exitEvent.is_set():
            with self.threadCondition:
                self.threadCondition.wait()
                if len(self.imageBuffer) > self.writeBufferSize:
                    while len(self.imageBuffer) > 0:
                        imageData = self.imageBuffer.popleft()
                        self.dumpImageToDisk(imageData)
                self.threadCondition.notify()

    def updateWriteDirs(self, updateDate, updateTime):
        logger.info("Changing output directory")

        self.currWriteDate = updateDate
        self.currWriteHour = updateTime
        next_hour = str((int(self.currWriteHour) + 1) % 24).zfill(2)
        self.recordingDir = os.path.join(self.recordingBaseDir,
                                         self.currWriteDate,
                                         "{}-{}".format(self.currWriteHour, next_hour))
        os.makedirs(self.recordingDir, exist_ok=True)

        logger.info("Output direcotry changed to %s" % self.recordingDir)

    def dumpImageToDisk(self, image):
        cv2.imwrite(
            os.path.join(self.recordingDir, "{}.jpg".format(image["timestamp"])),
            image["image"],
        )

    def addImageToBuffer(self, image):
        with self.imageBufferLock:
            self.imageBuffer.append(image)
        with self.threadCondition:
            self.threadCondition.notify()
