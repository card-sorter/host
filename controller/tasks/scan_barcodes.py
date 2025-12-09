"""
Scans barcodes and adds them to the barcodes table.
These barcodes can be used in future tasks to denote
pre-scanned bins or that it is the bottom of the bin.
"""
import asyncio
from typing import override

from controller.tasks.task import *
import cv2
import numpy as np

class ScanBarcodes(TaskController):
    def __init__(self, ctx:TaskContext):
        super().__init__(ctx)
        self.qr = cv2.QRCodeDetector()

    def scan_barcode(self, image: np.ndarray):
        text, _, _ = self.qr.detectAndDecode(image)
        return text

    @override
    async def run(self):
        target = None
        bins = self.ctx.default_bins
        for b in bins:
            img = await self.ctx.hal.scan_card(b, b)
            if img:
                if not self.scan_barcode(img):
                    b.scanned = True
                    target = b
                    bins.remove(b)
            else:
                raise Exception("Take image failed")
        async with asyncio.TaskGroup() as tg:
            for b in bins:
                while True:
                    img = await self.ctx.hal.scan_card(b, target)
                    if img:
                        text = self.scan_barcode(img)
                        if text:
                            tg.create_task(self.ctx.database.add_barcode(text))
                        else:
                            target = b
                            break

