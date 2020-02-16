# Copyright @ 2020 Alibaba. All rights reserved.
import numpy as np
from tf_serving_client import tf_serving_client
from sklearn.preprocessing import normalize
from skimage import transform as trans
import cv2

client_face_emb = tf_serving_client(["0.0.0.0:8500"], 'face_emb', 'default')

client_face_emb_partial = tf_serving_client(["0.0.0.0:8500"], 'face_emb_eyes', 'default')

client_mask = tf_serving_client(["0.0.0.0:8500"], 'face_mask', 'mask_detection')


def Extract(img, points):
    return get_embedding(align_face(img, points))

def align_face(img, points):
    points = [int(round(value.x)) for value in points.value] + [int(round(value.y)) for value in points.value]
    points = np.asarray(points)
    points = np.resize(points, new_shape=[2, 5]).transpose()
    return preprocess(img, landmark=points)

def read_image(img_path, **kwargs):
    mode = kwargs.get('mode', 'rgb')
    layout = kwargs.get('layout', 'HWC')
    if mode == 'gray':
        img = cv2.imread(img_path, cv2.CV_LOAD_IMAGE_GRAYSCALE)
    else:
        img = cv2.imread(img_path, cv2.CV_LOAD_IMAGE_COLOR)
        if mode == 'rgb':
            # print('to rgb')
            img = img[..., ::-1]
        if layout == 'CHW':
            img = np.transpose(img, (2, 0, 1))
    return img


def preprocess(img, landmark):
    landmark = np.asarray(landmark)
    image_size = [112, 112]
    src = np.array([
        [30.2946, 51.6963],
        [65.5318, 51.5014],
        [48.0252, 71.7366],
        [33.5493, 92.3655],
        [62.7299, 92.2041]], dtype=np.float32)
    if image_size[1] == 112:
        src[:, 0] += 8
    dst = landmark.astype(np.float32)
    tform = trans.SimilarityTransform()
    tform.estimate(dst, src)
    M = tform.params[0:2, :]
    img_aligned = cv2.warpAffine(img, M, (image_size[1], image_size[0]), borderValue=0.0)
    return img_aligned


def get_embedding(image_align, client=client_face_emb):
    image_align = image_align.astype(np.float32) / 127.5 - 1
    result = client.inference(input_dict={'images': image_align}, flip=True)
    emb = np.asarray(result.outputs['features'].float_val)
    emb = normalize(emb.reshape(1, -1)).reshape(-1)
    return emb

def detect_mask(image_align, client=client_mask):
    image_align = image_align.astype(np.float32) / 127.5 - 1
    result = client.inference(input_dict={'images': image_align}, flip=False)
    masks = np.asarray(result.outputs['masks'].int64_val)
    return bool(masks[0])


