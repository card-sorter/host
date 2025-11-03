"""
Scans barcodes and adds them to the barcodes table.
These barcodes can be used in future tasks to denote
pre-scanned bins or that it is the bottom of the bin.
"""
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
        for b in self.ctx.bins:
            img = await self.ctx.hal.scan_card(b, b)
            if img:
                if not self.scan_barcode(img):
                    b.scanned = True
                    target = b


