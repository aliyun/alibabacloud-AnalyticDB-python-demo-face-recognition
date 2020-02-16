cmake_minimum_required(VERSION 2.8)
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
include(ExternalProject)

# Adding customized cmake module for building boost
list(APPEND CMAKE_MODULE_PATH  "${CMAKE_SOURCE_DIR}/cmake/Modules/")

project(tutorial)

if(NOT DEFINED SeetaFace_DIR)
  message("SeetaFace_DIR not defined")
  set(SeetaFace_DIR "/Users/chaoshi/Projects/SeetaFace2/build/install/lib/cmake")
endif()
# 
find_package(SeetaFace)

if(SeetaFace_FOUND)
    message("${SeetaFace_INCLUDE_DIRS} ${SeetaFace_LIBRARIES}")
    set(LIBS_DEFINES ${LIBS_DEFINES} HAVE_SEETA_FACE)
    set(LIBS ${LIBS} ${SeetaFace_LIBRARIES})
    foreach(componet ${SeetaFace_LIBRARIES})
      message(${componet})
      INSTALL(FILES $<TARGET_FILE:${componet}>
      DESTINATION "${CMAKE_BINARY_DIR}")
    endforeach()
endif()
  # Find default python libraries and interpreter
  find_package(PythonInterp REQUIRED)
  find_package(PythonLibs REQUIRED)
  include(BuildBoost) # Custom module
  message("Boost: ${Boost_INCLUDE_DIR}")
  include_directories(${Boost_INCLUDE_DIR} ${PYTHON_INCLUDE_DIRS})
  link_directories(${Boost_LIBRARY_DIR})
  include_directories("${SeetaFace_DIR}/../../include/seeta")
  link_directories("${SeetaFace_DIR}/../../lib")
  # Build and link the pylib module
  add_library(seetafacelib SHARED seetafacelib.cpp)
  target_link_libraries(seetafacelib ${Boost_LIBRARIES} ${PYTHON_LIBRARIES} ${SeetaFace_LIBRARIES})
  add_dependencies(seetafacelib Boost)

  # Tweaks the name of the library to match what Python expects
  set_target_properties(seetafacelib PROPERTIES SUFFIX .so)
  set_target_properties(seetafacelib PROPERTIES PREFIX "")