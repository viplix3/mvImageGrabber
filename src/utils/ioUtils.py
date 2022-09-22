import cv2
import os
import threading
import logging

from collections import deque

logger = logging.getLogger(__name__)


class ImageIO:
    def __init__(self, recordingDir, bufferSize=50):
        self.recordingDir = recordingDir
        self.bufferSize = bufferSize
        self.imageBuffer = deque(maxlen=bufferSize)

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
            self.exitEvent.set()
            self.threadCondition.notify_all()
        self.imageBuffer.clear()
        self.imageIOThread.join()

    def imageIOThreadFunc(self):
        while not self.exitEvent.is_set():
            with self.threadCondition:
                self.threadCondition.wait()
                while len(self.imageBuffer) > 5:
                    image = self.imageBuffer.popleft()
                    self.dumpImageToDisk(image)

    def dumpImageToDisk(self, image):
        cv2.imwrite(
            os.path.join(self.recordingDir, "{}.jpg".format(image["timestamp"])),
            image["image"],
        )

    def addImageToBuffer(self, image):
        with self.imageBufferLock:
            self.imageBuffer.append(image)
        with self.threadCondition:
            self.threadCondition.notify_all()
