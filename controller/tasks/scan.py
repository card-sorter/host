import cv2
import numpy as np
from controller.tasks.task import *

class Scan(TaskController):
    def __init__(self, ctx: TaskContext):
        super().__init__(ctx)
        self.qr = cv2.QRCodeDetector()

    def scan_barcode(self, image: np.ndarray):
        text, _, _ = self.qr.detectAndDecode(image)
        return text

    async def run(self):
        # scan top card of every bin, find an empty one
        for b in self.ctx.bins:
            img = await self.ctx.hal.scan_card(b, b)
            if img:
                barcode = self.scan_barcode(img)
                if barcode:
                    b.barcode = barcode
        # if top card is barcode, load from db
        # if top card isn't in barcode table, then set bin as unscanned
        # set source bin to unscanned bin
        # while source bin not barcode in table(empty)
            # scan card from source bin and move to empty bin
            # crop and dewarp the image
            # save image to file
            # scan_barcode
            # create card object and put it into bin
            # update database with card info, bin info, and path to file
            # create scan_image task, pass card object

        #done