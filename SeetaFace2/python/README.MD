## **SeetaFace2 Python Wrapper**

### build steps
1. build  and install SeetaFace2

        cd SeetaFace2
        mkdir build
        cd build
        cmake .. -DCMAKE_INSTALL_PREFIX=`pwd`/install -DCMAKE_BUILD_TYPE=Release -DBUILD_EXAMPLE=OFF # 如果有 OpneCV，则设置为 ON
        cmake --build . --config Release --target install

2. build python wrapper

        cd SeetaFace2/python
        mkdir build
        cd build
        cmake -DSeetaFace_DIR=${SeetaFaceRoot}/build/install/lib/cmake .. 
        make seetafacelib
