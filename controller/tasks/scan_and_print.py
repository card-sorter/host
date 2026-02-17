"""
Scans one card from bin 1
Used for testing
"""
TASK_NAME = "Scan Single Card"
TASK_DESCRIPTION = "Scan a card and print the info"

import asyncio
import aiohttp
import json
from typing import override

import cv2

from controller.tasks.task import *

async def send_request(img):
    data = aiohttp.FormData()
    data.add_field('image',
                   img,
                   filename='image.jpg',
                   content_type='image/jpeg')
    async with aiohttp.ClientSession() as session:
        async with session.post("http://192.168.168.27:8000/scan", data=data) as response:
            if response.status == 200:
                result = await response.json()
                return result
            else:
                text = await response.text()
                print(json.dumps(text, indent = 4))
                raise Exception(f"failed to scan with status {response.status}: {response.text}")

class ScanAndPrint(TaskController):
    def __init__(self, ctx:TaskContext):
        super().__init__(ctx)



    @override
    async def run(self):
        target = None
        bins = self.ctx.default_bins
        print("taking img")
        img = await self.ctx.hal.scan_card(bins[0], bins[0])
        cv2.imwrite("test.jpg", img)
        success, encoded = cv2.imencode('.jpg', img)
        image_bytes = encoded.tobytes()
        result = await send_request(image_bytes)
        print(result)

__all__ = ['ScanAndPrint']
