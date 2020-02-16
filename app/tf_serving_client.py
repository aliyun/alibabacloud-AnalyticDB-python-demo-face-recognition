# Copyright @ 2020 Alibaba. All rights reserved.
import grpc
import numpy as np
import tensorflow as tf
from logger import logger
from tensorflow_serving.apis import predict_pb2
from tensorflow_serving.apis import prediction_service_pb2
import traceback


class tf_serving_client:
    def __init__(self, host_list, model_name, signature='default'):
        self.stubs = []
        self.host_list = host_list
        self.model_name = model_name
        self.signature_name = signature

        for host in host_list:
            channel = grpc.insecure_channel(host)
            stub = prediction_service_pb2.PredictionServiceStub(channel)
            self.stubs.append(stub)
        self.request = predict_pb2.PredictRequest()
        self.request.model_spec.name = model_name
        self.request.model_spec.signature_name = signature


    def inference(self, input_dict, flip=False):
        for key, image in input_dict.items():
            if flip:
                image = np.stack([image, np.fliplr(image)], axis=0)
                self.request.inputs[key].CopyFrom(
                    tf.contrib.util.make_tensor_proto(image, shape=list(image.shape)))
            else:
                self.request.inputs[key].CopyFrom(tf.contrib.util.make_tensor_proto(image, shape=[1] + list(image.shape)))

        for i in np.random.permutation(len(self.stubs)):
            try:
                result = self.stubs[i].Predict(self.request, 3)
            except Exception as e:
                logger.error("Failed to get result from tensorflow model server %s, model_name %s, signature_name %s"
                             %(self.host_list[i], self.model_name, self.signature_name))
                traceback.print_exc()
                continue
            return result

        logger.error("Failed to get result from all tensorflow model servers, model_name %s, signature_name %s"
                     % (self.model_name, self.signature_name))
        return None













