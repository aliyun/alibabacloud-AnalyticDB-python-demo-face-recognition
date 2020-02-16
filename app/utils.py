# Copyright @ 2020 Alibaba. All rights reserved.
from PIL import Image
from io import BytesIO
import base64

def pil_image_to_base64(pil_image):
    buf = BytesIO()
    pil_image.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue())

def base64_to_pil_image(base64_img):
    return Image.open(BytesIO(base64.b64decode(base64_img)))

def decode_image_base64(image_base64):
    return BytesIO(base64.b64decode(image_base64))
