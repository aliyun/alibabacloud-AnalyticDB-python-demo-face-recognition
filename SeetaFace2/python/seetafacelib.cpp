#include <boost/python.hpp>
#include <boost/python/numpy.hpp>
#include <assert.h>
#include <iostream>
#include "FaceDetector.h"
#include "FaceLandmarker.h"
#include "FaceDatabase.h"
#include "FaceTracker.h"
#include "FaceRecognizer.h"
#include "CStruct.h"

namespace bp = boost::python;

bp::tuple get_model(seeta::ModelSetting m)
{
  bp::list a;
  int i = 0;
  for (int i = 0; m.model[i] != NULL; ++i)
  {
    a.append(std::string(m.model[i]));
  }
  return bp::tuple(a);
}

SeetaImageData ndarray_to_SeetaImageData(bp::numpy::ndarray &x)
{
  SeetaImageData data;
  assert(x.get_nd() == 3);
  data.height = x.get_shape()[0];
  data.width = x.get_shape()[1];
  data.channels = x.get_shape()[2];
  data.data = (unsigned char *)x.get_data();
  return data;
}

bp::tuple wrap_data(SeetaFaceInfoArray const *s)
{
  bp::list a;
  for (int i = 0; i < s->size; ++i)
  {
    a.append(s->data[i]);
  }
  return bp::tuple(a);
}

bp::tuple wrap_tracking_data(SeetaTrackingFaceInfoArray const *s)
{
  bp::list a;
  for (int i = 0; i < s->size; ++i)
  {
    a.append(s->data[i]);
  }
  return bp::tuple(a);
}

bp::tuple wrap_PointVec(std::vector<SeetaPointF> const *s)
{
  bp::list a;
  for (int i = 0; i < s->size(); ++i)
  {
    a.append((*s)[i]);
  }
  return bp::tuple(a);
  ;
}

namespace seeta
{
namespace v2
{
class FaceRecognizer_wrapper : public FaceRecognizer
{
public:
  FaceRecognizer_wrapper(const SeetaModelSetting &setting) : FaceRecognizer(setting) {}

  bp::numpy::ndarray Extract_v2(bp::numpy::ndarray &image_np, std::vector<SeetaPointF> &points)
  {
    SeetaImageData image_data = ndarray_to_SeetaImageData(image_np);
    bp::numpy::ndarray feature = bp::numpy::zeros(bp::make_tuple(1024), bp::numpy::dtype::get_builtin<float>());
    Extract(image_data, &points[0], (float *)feature.get_data());
    return feature;
  }
};

class FaceDetector_wrapper : public FaceDetector
{
public:
  FaceDetector_wrapper(const SeetaModelSetting &setting) : FaceDetector(setting) {}
  FaceDetector_wrapper(const SeetaModelSetting &setting, int core_width, int core_height) : FaceDetector(setting, core_width, core_height) {}

  SeetaFaceInfoArray detect(bp::numpy::ndarray &x) const
  {
    SeetaImageData image_data = ndarray_to_SeetaImageData(x);
    return FaceDetector::detect(image_data);
  }
};

class FaceTracker_wrapper : public FaceTracker
{
public:
  FaceTracker_wrapper(const SeetaModelSetting &setting) : FaceTracker(setting) {}
  FaceTracker_wrapper(const SeetaModelSetting &setting, int core_width, int core_height) : FaceTracker(setting, core_width, core_height) {}

  SeetaTrackingFaceInfoArray track(bp::numpy::ndarray &x, int frame_no = -1) const
  {
    SeetaImageData image_data = ndarray_to_SeetaImageData(x);
    return FaceTracker::track(image_data, frame_no);
  }
};

class FaceLandmarker_wrapper : public FaceLandmarker
{
public:
  FaceLandmarker_wrapper(const SeetaModelSetting &setting) : FaceLandmarker(setting) {}

  std::vector<SeetaPointF> mark_wrapper(bp::numpy::ndarray &x, const SeetaRect &face) const
  {
    SeetaImageData image_data = ndarray_to_SeetaImageData(x);
    return FaceLandmarker::mark(image_data, face);
  }
};
} // namespace v2
} // namespace seeta

BOOST_PYTHON_MODULE(seetafacelib)
{
  bp::numpy::initialize();

  // Common class and function
  def("ndarray_to_SeetaImageData", &ndarray_to_SeetaImageData);

  bp::enum_<seeta::ModelSetting::Device>("Device")
    .value("AUTO", seeta::ModelSetting::AUTO)
    .value("CPU", seeta::ModelSetting::CPU)
    .value("GPU", seeta::ModelSetting::GPU)
    .export_values();
  
  bp::enum_<seeta::v2::FaceTracker::Property>("Property")
  .value("PROPERTY_MIN_FACE_SIZE", seeta::v2::FaceTracker::Property::PROPERTY_MIN_FACE_SIZE)
  .value("PROPERTY_THRESHOLD1", seeta::v2::FaceTracker::Property::PROPERTY_THRESHOLD1)
  .value("PROPERTY_THRESHOLD2", seeta::v2::FaceTracker::Property::PROPERTY_THRESHOLD2)
  .value("PROPERTY_THRESHOLD3", seeta::v2::FaceTracker::Property::PROPERTY_THRESHOLD3)
  .value("PROPERTY_VIDEO_STABLE", seeta::v2::FaceTracker::Property::PROPERTY_VIDEO_STABLE)
  .export_values();


  bp::class_<std::vector<SeetaPointF>>("PointVec")
      .add_property("value", wrap_PointVec);

  bp::class_<SeetaPointF>("SeetaPointF")
      .def_readwrite("x", &SeetaPointF::x)
      .def_readwrite("y", &SeetaPointF::y);

  bp::class_<SeetaRect>("SeetaRect")
      .def_readwrite("x", &SeetaRect::x)
      .def_readwrite("y", &SeetaRect::y)
      .def_readwrite("height", &SeetaRect::height)
      .def_readwrite("width", &SeetaRect::width);

  bp::class_<SeetaFaceInfo>("SeetaFaceInfo")
      .def_readwrite("pos", &SeetaFaceInfo::pos)
      .def_readwrite("score", &SeetaFaceInfo::score);

  bp::class_<SeetaFaceInfoArray>("SeetaFaceInfoArray")
      .def_readwrite("size", &SeetaFaceInfoArray::size)
      .add_property("data", wrap_data);

  bp::class_<SeetaImageData>("SeetaImageData")
      .def_readwrite("width", &SeetaImageData::width)
      .def_readwrite("height", &SeetaImageData::height)
      .def_readwrite("channels", &SeetaImageData::channels)
      .def_readwrite("data", &SeetaImageData::data);

  bp::class_<seeta::ModelSetting>("ModelSetting", bp::init<std::string, seeta::ModelSetting::Device, int>())
      .def_readwrite("id", &SeetaModelSetting::id)
      .def_readwrite("device", &SeetaModelSetting::device)
      .add_property("model", make_function(get_model));

  bp::class_<SeetaTrackingFaceInfoArray>("SeetaTrackingFaceInfoArray")
      .def_readwrite("size", &SeetaTrackingFaceInfoArray::size)
      .add_property("data", wrap_tracking_data);

  bp::class_<SeetaTrackingFaceInfo>("SeetaTrackingFaceInfo")
      .def_readwrite("pos", &SeetaTrackingFaceInfo::pos)
      .def_readwrite("score", &SeetaTrackingFaceInfo::score)
      .def_readwrite("frame_no", &SeetaTrackingFaceInfo::frame_no)
      .def_readwrite("PID", &SeetaTrackingFaceInfo::PID);

  //face detector
  bp::class_<seeta::v2::FaceDetector_wrapper, boost::noncopyable>("FaceDetector", bp::init<const seeta::ModelSetting &>())
      .def(bp::init<const seeta::ModelSetting &, int, int>())
      .def("detect", &seeta::v2::FaceDetector_wrapper::detect);

  //face landmarker
  bp::class_<seeta::v2::FaceLandmarker_wrapper, boost::noncopyable>("FaceLandmarker", bp::init<const seeta::ModelSetting &>())
      // .def("mark", static_cast<std::vector<SeetaPointF> (seeta::v2::FaceLandmarker::*)(const SeetaImageData &, const SeetaRect &) const>(&seeta::v2::FaceLandmarker::mark));
      .def("mark", &seeta::v2::FaceLandmarker_wrapper::mark_wrapper);

  //face recognizier
  bp::class_<seeta::v2::FaceRecognizer_wrapper, boost::noncopyable>("FaceRecognizer", bp::init<const seeta::ModelSetting &>())
      .def("Extract", &seeta::v2::FaceRecognizer_wrapper::Extract_v2)
      .def("Extract", &seeta::v2::FaceRecognizer_wrapper::Extract_v2)
      ;

  //face tracker
  bp::class_<seeta::v2::FaceTracker_wrapper, boost::noncopyable>("FaceTracker", bp::init<const seeta::ModelSetting &>())
      .def("track", &seeta::v2::FaceTracker_wrapper::track)
      .def("set", &seeta::v2::FaceTracker_wrapper::set )
      .def("get", &seeta::v2::FaceTracker_wrapper::get );

  //face recognizier
  bp::class_<seeta::v2::FaceDatabase, boost::noncopyable>("FaceDatabase", bp::init<const seeta::ModelSetting &>())
      // .def("detect", &seeta::v2::FaceRecognizer::detect)
      ;
}