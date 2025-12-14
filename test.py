import cv2
import aiohttp
import asyncio

async def send_request(img):
    data = aiohttp.FormData()
    data.add_field('image',
                   img,
                   filename='image.png',
                   content_type='image/png')
    async with aiohttp.ClientSession() as session:
        async with session.post("http://192.168.168.27:8000/scan", data=data) as response:
            if response.status == 200:
                result = await response.json()
                return result
            else:
                text = await response.text()
                raise Exception(f"failed to scan with status {response.status}: {response.text}")
            
async def run():
            img = cv2.imread("image.png")
            success, encoded = cv2.imencode('image.png', img)
            image_bytes = encoded.tobytes()
            result = await send_request(image_bytes)
            print(result)

if __name__ == "__main__":
    asyncio.run(run())