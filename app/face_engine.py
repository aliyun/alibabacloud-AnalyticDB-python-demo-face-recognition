# Copyright @ 2020 Alibaba. All rights reserved.
# coding:utf-8
import os
from face_database import face_database
import seetafacelib as st
from PIL import Image
import numpy as np
import multiprocessing
import time
import cv2
from face_utility import Extract, align_face, get_embedding
import face_utility
import datetime


class face_engine:
    def __init__(self, face_db, model_dir, dist_thre, image_height=360, image_width=640):
        self.face_db = face_db
        # initialize the models
        self.fd = st.FaceDetector(st.ModelSetting(os.path.join(model_dir, "fd_2_00.dat"), st.Device.CPU, 1),
                                  image_width, image_height)
        self.ft = st.FaceTracker(st.ModelSetting(os.path.join(model_dir, "fd_2_00.dat"), st.Device.CPU, 1))

        # 降低tracker 人脸检测阈值提升带口罩情况下的召回率, 默认值0.85
        self.ft.set(st.Property.PROPERTY_MIN_FACE_SIZE, 128)
        self.ft.set(st.Property.PROPERTY_THRESHOLD3, 0.6)
        self.fl = st.FaceLandmarker(st.ModelSetting(os.path.join(model_dir, "pd_2_00_pts5.dat"), st.Device.CPU, 1))
        # distance threshold
        self.dist_thre = dist_thre
        # the pid of the last frame output by tracker (the largest face)
        self.pid_last = -1
        # if the key frame has been detected or not
        self.key_frame_detected = False
        # the frame number of the first frame when the current face was tracked
        self.frame_no_first = -1
        # the time when the current face was first tracked
        self.time_first = -1
        # create tables if they are not existed
        self.face_db.create_table()

    def run_process(self, schema, frame):
        """
        Process a single video frame
        :param frame: a video frame
        :return:
        pos: the position of detected face
        query_result: the query result, True if found, False if not found, None if this frame is not the key frame
        name: the name of found person
        pid: pid of the person in database
        key_frame: True is the input frame is the key frame
        key_frame_detected: True if key frame of the current tracked face has been detected
        """
        track_result = self.ft.track(frame, -1)
        pos = None
        query_result = None
        key_frame = False
        name = None
        pid = None
        records = None
        has_mask = None
        if len(track_result.data) > 0:
            face = self.get_largest_face(track_result.data)
            pos = face.pos
            if self.key_frame_detection(track_result):
                key_frame = True
                # extract face feature and compare
                points = self.fl.mark(frame, pos)
                img_align = align_face(frame, points)
                has_mask = face_utility.detect_mask(img_align)
                if has_mask:
                    feature = face_utility.get_embedding(img_align, face_utility.client_face_emb_partial)
                else:
                    feature = face_utility.get_embedding(img_align, face_utility.client_face_emb)
                query_result, name, pid = self.query(schema, feature, has_mask)
                if not query_result:
                    # 如果人脸识别失败 则继续识别
                    self.key_frame_detected = False
                    self.time_first = time.time() + 1
                else:
                    begin = datetime.datetime.now() - datetime.timedelta(days=2)
                    begin = begin.strftime("%Y-%m-%d %H:%M:%S")
                    records = self.face_db.get_record_family(schema, pid, begin)

        return pos, query_result, name, pid, key_frame, self.key_frame_detected, records, has_mask

    def get_face_area(self, face):
        '''
        Get the area of detected face
        :param face: detected face object
        :return: the area in number of pixels
        '''
        return face.pos.width * face.pos.height

    def get_largest_face(self, faces):
        """
        :param faces: list of face object
        :return: the face object with largest area
        """
        idx = np.argmax([self.get_face_area(face) for face in faces])
        return faces[idx]

    def key_frame_detection(self, track_result):
        """
        Determine if the input frame is the key frame. Currently, when the face was tracked for over 1 second and the
        key frame has not been detected, this frame will be treated as the key frame.
        :param track_result: track result returned by tracker
        :return: True if the current frame is the key frame
        """
        data = track_result.data[0]
        pid = data.PID
        if pid != self.pid_last:
            self.key_frame_detected = False
            self.pid_last = pid
            self.frame_no_first = data.frame_no
            self.time_first = time.time()

        if not self.key_frame_detected and time.time() - self.time_first > 1.:
            self.key_frame_detected = True
            return True
        else:
            return False

    def query(self, schema, feature, has_mask=False):
        """
        Query in the database
        :param feature: the feature vector
        :return:
        """
        query_result = False
        name = None
        pid = None
        result = self.face_db.query_top_n_above(schema, feature, 1, thre=self.dist_thre, has_mask=has_mask)
        if len(result) == 0:
            return query_result, name, pid
        query_result = True
        name = result[0][1]
        pid = result[0][0]
        dist = result[0][4]
        print "name %s, feature distance: %f" %(name, dist)
        # record the access
        self.face_db.record_access(schema, pid)
        return query_result, name, pid

    def extract_feature(self, frame, points=None):
        if not points:
            # detect face
            frame = cv2.resize(frame, (frame.shape[1], frame.shape[0]))
            detect_result = self.fd.detect(frame)
            if len(detect_result.data) == 0:
                return None
            # detect landmark
            points = self.fl.mark(frame, detect_result.data[0].pos)
        # feature = self.fr.Extract(frame, points)
        t = time.time()
        feature = Extract(frame, points)
        print "time inference %f"%(time.time() - t)
        return feature

    def create_table(self):
        self.face_db.create_table()

    def register(self, schema, frame, pid, name, gender, age, address):
        feature = self.extract_feature(frame=frame)
        if feature is None:
            return False
        return self.face_db.register(schema, feature, pid, name, gender, age, address)

    def register_mask(self, schema, frame, pid, name, gender, age, address):
        image_align = self.detect_and_align_face(frame)
        if image_align is None:
            return False
        # 提取全脸特征
        feature = get_embedding(image_align, face_utility.client_face_emb)
        # 提取眼部+额头特征
        feature_partial = get_embedding(image_align, face_utility.client_face_emb_partial)
        return self.face_db.register_mask(schema, feature, feature_partial, pid, name, gender, age, address)

    def detect_and_align_face(self, frame, points=None):
        if not points:
            # detect face
            frame = cv2.resize(frame, (frame.shape[1], frame.shape[0]))
            detect_result = self.fd.detect(frame)
            if len(detect_result.data) == 0:
                return None
            # detect landmark
            points = self.fl.mark(frame, detect_result.data[0].pos)
            return align_face(frame, points)

    def load_records(self, image_paths, names, image_root=''):
        assert (len(image_paths) == len(names))
        for i in range(len(image_paths)):
            image_path = image_paths[i]
            name = names[i]
            image = Image.open(os.path.join(image_root, image_path)).convert("RGB")
            image_np = np.asarray(image, dtype=np.uint8)
            image_np = cv2.resize(image_np, (image_np.shape[1] * 2, image_np.shape[0] * 2))
            # convert to BGR
            image_np = image_np[:, :, ::-1]
            self.register(image_np, name)
            print "Registered %d/%d images" % (i + 1, len(image_paths))

    def get_recent_access_record(self, schema, num_record=20):
        return self.face_db.get_recent_access_record(schema, num_record)

