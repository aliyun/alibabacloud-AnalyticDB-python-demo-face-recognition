# Copyright @ 2020 Alibaba. All rights reserved.
#! coding: utf-8
from sys import stdout
import logging
from flask import Flask, render_template, Response, send_from_directory, jsonify, request, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from flask_api import status
import os
from PIL import Image
import numpy as np
import face_application
from logger import logger
import traceback
ip = os.environ.get("APP_IP")
port = os.environ.get("APP_PORT")
if not ip:
    ip = '0.0.0.0'
if not port:
    port = 8000
dir_path = os.path.dirname(os.path.realpath(__file__))
static_url = os.path.join(dir_path, 'frontend')
app = Flask(__name__, static_url_path=static_url, template_folder=static_url)
app.logger.addHandler(logging.StreamHandler(stdout))
app.config['SECRET_KEY'] = 'secret!'
app.config['DEBUG'] = True
login_manager = LoginManager()
login_manager.init_app(app)
app.secret_key = 'secret_key'

class User():
    def __init__(self, user_id, name, email):
        self.user_id = user_id
        self.name = name
        self.email = email

    def to_json(self):
        return {
            "user_id": self.user_id,
            "name": self.name,
            "email": self.email
        }

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.user_id)


@app.route('/<path:path>')
def page(path):
    return send_from_directory(app.static_url_path, path)


@app.route('/')
@app.route('/login_page')
def login_page():
    return render_template('login.html')

@app.route('/action/register', methods=['POST'])
@login_required
def register():
    try:
        print request
        image_file = request.files['photo']
        name = request.form.get('name')
        image_np = np.asarray(Image.open(image_file).convert('RGB'), dtype=np.uint8)
        image_np = image_np[:, :, ::-1]
        pid = request.form.get('pid')
        gender = request.form.get('gender')
        age = request.form.get('age')
        louhao = request.form.get('louhao')
        danyuan = request.form.get('danyuan')
        menpaihao = request.form.get('menpai')
        address= None

        if louhao is not None and danyuan is not None and menpaihao is not None:
            address = "%s-%s-%s"%(louhao, danyuan, menpaihao)
        if name == "" or gender == "" or address == "":
            return jsonify({"code": status.HTTP_400_BAD_REQUEST,
                            "msg": u"register fail! 提交信息不完整"})

        if not face_application.register(current_user.name, image_np, pid, name, gender, age, address):
            return jsonify({"code": status.HTTP_400_BAD_REQUEST,
                            "msg": "register fail! The feature cannot be extracted from this image! "})

    except:
        logger.error(traceback.print_exc())
        return jsonify({"code": status.HTTP_500_INTERNAL_SERVER_ERROR, "msg": "Internal error "})
    return jsonify({"code": status.HTTP_200_OK, "msg": "register success!"})

@app.route('/action/record_query', methods=['POST'])
@login_required
def record_query():
    try:
        image_file = request.files['photo']
        name = request.form.get('name')
        # load image into ndarray
        print image_file
        if image_file is not None:
            image_np = np.asarray(Image.open(image_file).convert('RGB'), dtype=np.uint8)
            image_np = image_np[:, :, ::-1]
        else:
            image_np = None
        gender = request.form.get('gender')
        age = request.form.get('age')
        begin = request.form .get('begin')
        end = request.form .get('end')
        result= face_application.get_record(current_user.name, image_np, name, gender, age, begin, end)
        return jsonify({"code": status.HTTP_200_OK, 'result': result, "msg": ""})

    except:
        logger.error(traceback.print_exc())
        return jsonify({"code": status.HTTP_500_INTERNAL_SERVER_ERROR, "msg": "Internal error "})

@app.route('/process', methods=['POST'])
@login_required
def process():
    try:
        image_np = np.asarray(Image.open(request.files['image']).convert("RGB"), dtype=np.uint8)
        # convert bgr to bgr
        image_np = image_np[:, :, ::-1]
        result = face_application.process_one(current_user.name, image_np)
        return jsonify({"code": status.HTTP_200_OK, 'result': result, "msg": ""})
    except:
        logger.error(traceback.print_exc())
        return jsonify({"code": status.HTTP_500_INTERNAL_SERVER_ERROR, 'result': None, "msg": ""})

@app.route('/get_record', methods=['get'])
@login_required
def get_record():
    try:
        result = face_application.get_recent_access_record(current_user.name)
        return jsonify({"code": status.HTTP_200_OK, 'result': result, "msg": ""})
    except:
        logger.error(traceback.print_exc())
        return jsonify({"code": status.HTTP_500_INTERNAL_SERVER_ERROR, 'result': None, "msg": ""})

@app.route('/action/exec_sql', methods=['POST'])
@login_required
def exec_sql():
    try:
        sql = request.form.get('sql')
        result = face_application.exec_sql(sql)
        return jsonify({"code": status.HTTP_200_OK, 'result': result, "msg": ""})
    except:
        logger.error(traceback.print_exc())
        return jsonify({"code": status.HTTP_500_INTERNAL_SERVER_ERROR, 'result': None, "msg": ""})

@app.route('/register', methods=['POST'])
def user_register():
    user_name = request.form.get("username")
    password = request.form.get("password")
    email = request.form.get("email")
    try:
        if face_application.face_db.check_user_exists(user_name):
            return jsonify({'result': False, "msg": u"账户已存在"})
        face_application.face_db.user_register(user_name, password, email)
        return jsonify({'result': True, "msg": u"注册成功"})
    except Exception, e:
        logger.error(traceback.print_exc())
        return jsonify({'result': False, "msg": u"注册失败, 内部错误"})


@app.route('/login', methods=['POST'])
def login():
    user_name = request.form.get("username")
    password = request.form.get("password")
    try:
        if face_application.face_db.login(user_name, password):
            user_id, name, email = face_application.face_db.get_user_info(user_name)
            login_user(User(user_id, name, email))
            return jsonify({'result': True, "msg": ""})
        else:
            return jsonify({'result': False, "msg": u"账户或密码错误"})
    except Exception, e:
        logger.error(traceback.print_exc())
        return jsonify({'result': False, "msg": u"登陆失败, 内部错误"})

@app.route('/logout', methods=['GET'])
def logout():
    logout_user()
    return redirect(url_for("login_page"))

@login_manager.user_loader
def load_user(user_id):
    try:
        user_id, name, email = face_application.face_db.get_user_info_by_id(user_id)
        return User(user_id, name, email)
    except Exception, e:
        logger.error(traceback.print_exc())
        return None



if __name__ == '__main__':
    Flask.run(app, host=ip, port=port)
