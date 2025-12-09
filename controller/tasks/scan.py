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

    async def scan_api(self, image: np.ndarray):
        pass

    async def run(self):
        # scan top card of every bin, find an empty one
        target = None
        for b in self.ctx.default_bins:
            img = await self.ctx.hal.scan_card(b, b)
            if img:
                barcode = self.scan_barcode(img)
                if barcode:
                    # load bin from db
                    b.barcode = barcode
                    b.id = await self.ctx.database.check_barcode(barcode)
                    if b.id:
                        b.clear()
                        b.extend(await self.ctx.database.load_bin(b.id))
                        b.scanned = True
                        if b.empty:
                            target = b

        for b in self.ctx.default_bins:
            if not b.empty:


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