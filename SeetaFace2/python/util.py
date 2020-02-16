from io import BytesIO
import base64


def decode_image_base64(image_base64):
    return BytesIO(base64.b64decode(image_base64))