$(document).ready(function(){
    let namespace = "/test";
    let video = document.querySelector("#videoElement");
    let canvas = document.getElementById('canvasElement');
    canvas.width = 640;
    canvas.height = 360;
    let ctx = canvas.getContext('2d');
    let message_tag = document.getElementById('heading_message');
    let message_tag2 = document.getElementById('message2');

    let drawCanvas = document.getElementById('canvasElement2');
    drawCanvas.width = 640;
    drawCanvas.height = 360;
    // document.body.appendChild(drawCanvas);
    let drawCtx = drawCanvas.getContext("2d");

    var localMediaStream = null;

    var constraints = {
    video: {
      width: { min: 960 },
      height: { min: 480 }
    }
    };

    navigator.mediaDevices.getUserMedia(constraints).then(function(stream) {
    video.srcObject = stream;
    localMediaStream = stream;

    ctx.drawImage(video, 0, 0, video.videoWidth, video.videoHeight, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(postFile, 'image/jpeg');

    }).catch(function(error) {
    console.log(error);
    });

    const apiServer = window.location.origin + '/process';

    function sleep(seconds){
        var waitUntil = new Date().getTime() + seconds*1000;
        while(new Date().getTime() < waitUntil) true;

    }

    //draw boxes and labels on each detected object
    function drawBoxes(object) {

        //clear the previous drawings
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        let x = object[0];
        let y = object[1];
        let width = object[2] - x;
        let height = object[3] - y;

        // //flip the x axis if local video is mirrored
        // if (mirror) {
        //     x = drawCanvas.width - (x + width)
        // }

        // drawCtx.fillText(object.class_name + " - " + Math.round(object.score * 100) + "%", x + 5, y + 20);
        drawCtx.strokeStyle = 'green';
        drawCtx.lineWidth = 3;
        // ctx.beginPath();
        drawCtx.strokeRect(x, y, width, height);

    }

    function drawTex(msg, x, y){
        drawCtx.font = "15px Arial";
        drawCtx.fillStyle = 'green';
        drawCtx.fillText(msg, x, y);
    }

    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    //Add file blob to a form and post
    function postFile(file) {

        //Set options as form data
        let formdata = new FormData();
        formdata.append("image", file);

        let xhr = new XMLHttpRequest();
        xhr.open('POST', apiServer, true);
        xhr.onload = async function () {
            if (this.status === 200) {

                // console.log(this.response)
                let objects = JSON.parse(this.response);
                let pos = objects.result.pos;
                let query_result = objects.result.query_result;
                drawCtx.drawImage(canvas, 0, 0);

                if (pos && objects.result.key_frame_detected === false) {
                    message_tag.innerHTML = "人脸识别中..., 请看摄像头"
                }

                //draw the boxes
                if (pos)
                    drawBoxes(pos);
                else{
                    console.log("请进入摄像头区域");
                    message_tag.innerHTML = "请进入摄像头区域";
                }

                if (query_result === true){
                    msg = "欢迎, "+objects.result.name;
                    if (objects.result.has_mask === true){
                        msg = msg + ' (您带了口罩,使用眼部,额头特征进行识别)'
                    }
                    drawTex(msg, 50, 50);
                    message_tag.innerHTML = msg;
                    $("#record_message_head").html(objects.result.name+"的家庭成员2日内累计进出"+objects.result.num_records+"次,以下是来访记录:");
                    $("#record_message").html(objects.result.records);
                    await sleep(3000);
                    message_tag.innerHTML = "人脸识别已通过";

                }
                else if(query_result == false){
                    msg = "未注册用户"
                    if (objects.result.has_mask === true){
                        msg = msg + ' (您带了口罩,使用眼部,额头特征进行识别)'
                    }
                    drawTex(msg, 50, 50);
                    message_tag.innerHTML = msg;
                    await sleep(1000);
                }
                //Save and send the next image
                ctx.drawImage(video, 0, 0, video.videoWidth, video.videoHeight, 0, 0, canvas.width, canvas.height);
                canvas.toBlob(postFile, 'image/jpeg');
            }
            else {
                console.error(xhr);
            }
        };
        xhr.send(formdata);
    }

});

