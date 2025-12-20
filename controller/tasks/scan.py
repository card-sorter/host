import cv2
import numpy as np
from controller.tasks.task import *
from pyzbar.pyzbar import decode
import aiohttp

class Scan(TaskController):
    def __init__(self, ctx: TaskContext):
        super().__init__(ctx)
        self.qr = cv2.QRCodeDetector()

    def scan_barcode(self, image: np.ndarray):
        barcodes = decode(image)
        for b in barcodes:
            return b.data.decode('utf-8')
        return None

    async def scan_api(self, image: np.ndarray):
            data = aiohttp.FormData()
            data.add_field('image',
                        image,
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

    async def run(self):
        # scan top card of every bin, find an empty one
        target = None
        source_bins = []
        for b in self.ctx.default_bins:
            img = await self.ctx.hal.scan_card(b, b)
            if img is not False:
                barcode = self.scan_barcode(img)
                if barcode:
                    # load bin from db
                    b.barcode = barcode
                    b.id = await self.ctx.database.check_barcode(barcode)
                    if b.id:
                        b.clear()
                        #b.extend(await self.ctx.database.load_bin(b.id))
                        b.scanned = True
                        if b.empty:
                            target = b
                    else:
                        target = b
                else:
                    source_bins.append(b)
        print("part 2")
        print(source_bins)
        for b in source_bins:
            while True:
                img = await self.ctx.hal.scan_card(b, target)
                if img is not False:
                    barcode = self.scan_barcode(img)
                    if barcode:
                        await self.ctx.hal.move_card(target, b)
                        target.scanned = True
                        target = b
                        break
                    success, encoded = cv2.imencode('.jpg', img)
                    image_bytes = encoded.tobytes()
                    card = await self.scan_api(image_bytes)
                    print(card[0])
                    target.append(card[0]['details']['name'])
        print(self.ctx.default_bins)
        await asyncio.sleep(0)





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

__all__ = ["Scan"]