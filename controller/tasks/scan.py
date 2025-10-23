from controller.tasks.task import *
import cv2
import numpy as np

class Scan(TaskController):
    def __init__(self, ctx: TaskContext):
        super().__init__(ctx)
        self.qr = cv2.QRCodeDetector()

    def scan_barcode(self, image: np.ndarray):
        text, _, _ = self.qr.detectAndDecode(image)
        return text

    async def run(self):
        # scan top card of every bin, find an empty one
        # if top card is barcode, load from db
        # if top card isn't a barcode, then set bin as empty
        # set source bin to unscanned bin
        # while source bin not barcode (empty)
            # scan card from source bin and move to empty bin
            # crop and dewarp the image
            # save image to file
            # scan_barcode
            # create card object and put it into bin
            # create scan_image task, pass card object

        #done


        pass
