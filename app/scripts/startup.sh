#!/usr/bin/env bash
set -ex
LOG_DIR=/home/app/logs
mkdir -p $LOG_DIR
/usr/bin/tensorflow_model_server \
--port=$TF_SERVING_PORT  \
--model_config_file=/home/app/tf_serving/config.conf \
--enable_batching=true  \
--batching_parameters_file=/home/app/tf_serving/batching.conf > ${LOG_DIR}/tensorflow.stdout 2>${LOG_DIR}/tensorflow.stderr &
python app.py