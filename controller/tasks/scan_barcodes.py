"""
Scans barcodes and adds them to the barcodes table.
These barcodes can be used in future tasks to denote
pre-scanned bins or that it is the bottom of the bin.
"""
import asyncio
from typing import override

from controller.tasks.task import *
from pyzbar.pyzbar import decode
import cv2
import numpy as np

class ScanBarcodes(TaskController):
    def __init__(self, ctx:TaskContext):
        super().__init__(ctx)
        self.qr = cv2.QRCodeDetector()

    def scan_barcode(self, image: np.ndarray):
        barcodes = decode(image)
        for b in barcodes:
            print(b.data.decode('utf-8'))
            return b.data.decode('utf-8')
        return None

    @override
    async def run(self):
        target = None
        bins = self.ctx.default_bins
        print(bins)
        for b in bins:
            img = await self.ctx.hal.scan_card(b, b)
            if img is not False:
                if self.scan_barcode(img) is None:
                    b.scanned = True
                    target = b
                    bins.remove(b)
                    break
            else:
                raise Exception("Take image failed")
        async with asyncio.TaskGroup() as tg:
            print(bins)
            for b in bins:
                print(b)
                while True:
                    img = await self.ctx.hal.scan_card(b, target)
                    if img is not False:
                        text = self.scan_barcode(img)
                        print(text)
                        if text:
                            tg.create_task(self.ctx.database.add_barcode(text))
                        else:
                            target = b
                            break
        return

__all__ = ["ScanBarcodes"]

