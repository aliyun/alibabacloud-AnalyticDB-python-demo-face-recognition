# Copyright @ 2020 Alibaba. All rights reserved.
# -*- coding: utf-8 -*-
import os
import sys
import json
import datetime
from app_config import CONFIG

dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.split(dir)[0])
from face_engine import face_engine
from face_database import face_database
import cv2

def default(o):
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()

database_config = CONFIG['database_config']
face_engine_config = CONFIG['face_engine_config']
host = database_config['host']
database = database_config['database']
user = database_config['user']
password = database_config['password']
port = database_config['port']

model_dir = face_engine_config['model_dir']
dist_thre = face_engine_config['dist_thre']
dist_measure = face_engine_config['dist_measure']
image_height = face_engine_config['image_height']
image_width = face_engine_config['image_width']

face_db = face_database(database=database, host=host, port=port, user=user, password=password, app_name="test", distance_measure=dist_measure)
# Load models
fe = face_engine(face_db, model_dir=model_dir, dist_thre=dist_thre, image_height=image_height, image_width=image_width)

def register(schema, image_np, pid, name, gender, age, address):
    image_np = cv2.resize(image_np, (image_np.shape[1], image_np.shape[0]))
    return fe.register_mask(schema, image_np, pid, name, gender, age, address)

def process_one(schema, image_np):
    image_np = cv2.resize(image_np, (image_np.shape[1], image_np.shape[0]))
    pos, query_result, name, pid, key_frame, key_frame_detected, records, has_mask = fe.run_process(schema, image_np)
    record_str = None
    num_records = 0

    if records:
        record_str = format_table(records, ("来访时间", "姓名", "住址", "ID"))
        num_records = len(records)
    if pos:
        pos = [pos.x, pos.y, pos.x + pos.width, pos.y + pos.height]
    result = {
        "pos": pos,
        "query_result": query_result,
        "name": name,
        "pid": pid,
        "key_frame": key_frame,
        "key_frame_detected": key_frame_detected,
        "records": record_str,
        "num_records": num_records,
        "has_mask": has_mask
    }
    return result


def get_recent_access_record(schema):
    result = fe.get_recent_access_record(schema, 20)
    result = [[val[0], val[1], val[2], val[3].strftime("%Y-%m-%d %H:%M:%S")] for val in result]
    return result


def exec_sql(sql):
    rows, _ = face_db.db.sql_worker(sql, False, True)
    rowstr = format_table(rows)
    return json.dumps(rowstr, ensure_ascii=False, indent=2, default=default)


def gen_query(schema, image_np, name, gender, age, begin, end, threshold=0.8):
    if image_np is not None and image_np != "":
        feature = fe.extract_feature(image_np)
    else:
        feature = None
    if feature is not None:
        sql = "select * from (select name,gender,age,time,(feature <-> array[%s]) as distance from person_test, face_feature_test, access_record_test " \
              "where person_test.pid = access_record_test.pid " \
              "and person_test.pid = face_feature_test.pid " % ",".join([str(x) for x in feature])
    else:
        sql = "select name,gender,age,time from person_test, face_feature_test, access_record_test " \
              "where person_test.pid = access_record_test.pid " \
              "and person_test.pid = face_feature_test.pid "
    if name is not None and name != "":
        sql += "and name = '%s' " % name
    if gender is not None and gender != "":
        sql += "and gender = '%s' " % gender
    if age is not None and age != "":
        sql += "and age = %s " % age
    if begin is not None and begin != "":
        sql += "and time >= '%s' " % begin
    if end is not None and end != "":
        sql += "and time <= '%s' " % end
    if feature is not None:
        sql += "order by distance limit 10) as b where distance < %f; " % threshold
    elif begin is not None and begin != "":
        sql += "order by time limit 10;"
    else:
        sql += "order by time desc limit 10;"
    return sql

def get_record(schema, image_np, name, gender, age, begin, end):
    if image_np is not None and image_np != "":
        image_np = cv2.resize(image_np, (image_np.shape[1], image_np.shape[0]))
        feature = fe.extract_feature(image_np)
    else:
        feature = None

    rows = face_db.get_record(schema, feature, name, gender, age, begin, end, fe.dist_thre)
    rowstr = format_table(rows, ("姓名","性别","年龄", "来访时间", "人脸特征距离"))
    return rowstr

def format_table(rows, head=None):
    rowstr = '<table class="table table-bordered">'
    if head:
        rowstr += '<thead><tr>'
        for item in head:
            rowstr += '<th>'
            rowstr += str(item)
            rowstr += '</th>'
        rowstr += '</tr></thead>'
    rowstr += '<tbody>'
    if type(rows) == list:
        for row in rows:
            rowstr += "<tr>"
            max_id = len(row) - 1
            for i, item in enumerate(row):
                rowstr += "<td>"
                rowstr += str(item)
                rowstr += "</td>"
            rowstr += "</tr>"
    rowstr += "</tbody></table>"
    return rowstr

def drop_table():
    face_db.drop_tables()

