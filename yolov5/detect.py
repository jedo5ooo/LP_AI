# YOLOv5 🚀 by Ultralytics, AGPL-3.0 license
"""
Run YOLOv5 detection inference on images, videos, directories, globs, YouTube, webcam, streams, etc.
# 이미지 얼굴 식별 + 나머지 모자이크
Usage - sources:
    $ python detect.py --weights yolov5s.pt --source 0                               # webcam
                                                     img.jpg                         # image
                                                     vid.mp4                         # video
                                                     screen                          # screenshot
                                                     path/                           # directory
                                                     list.txt                        # list of images
                                                     list.streams                    # list of streams
                                                     'path/*.jpg'                    # glob
                                                     'https://youtu.be/LNwODJXcvt4'  # YouTube
                                                     'rtsp://example.com/media.mp4'  # RTSP, RTMP, HTTP stream

Usage - formats:
    $ python detect.py --weights yolov5s.pt                 # PyTorch
                                 yolov5s.torchscript        # TorchScript
                                 yolov5s.onnx               # ONNX Runtime or OpenCV DNN with --dnn
                                 yolov5s_openvino_model     # OpenVINO
                                 yolov5s.engine             # TensorRT
                                 yolov5s.mlmodel            # CoreML (macOS-only)
                                 yolov5s_saved_model        # TensorFlow SavedModel
                                 yolov5s.pb                 # TensorFlow GraphDef
                                 yolov5s.tflite             # TensorFlow Lite
                                 yolov5s_edgetpu.tflite     # TensorFlow Edge TPU
                                 yolov5s_paddle_model       # PaddlePaddle
"""

import argparse
import csv
import os
import platform
import sys
import pathlib
# import face_recognition
from pathlib import Path
import numpy as np
from deepface import DeepFace
import torch
from tensorflow import keras
import time
import json

temp = pathlib.PosixPath
pathlib.PosixPath = pathlib.WindowsPath

FILE = Path(__file__).resolve()
ROOT = FILE.parents[0]  # YOLOv5 root directory
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))  # add ROOT to PATH
ROOT = Path(os.path.relpath(ROOT, Path.cwd()))  # relative

from ultralytics.utils.plotting import Annotator, colors, save_one_box

from models.common import DetectMultiBackend
from utils.dataloaders import IMG_FORMATS, VID_FORMATS, LoadImages, LoadScreenshots, LoadStreams
from utils.general import (
    LOGGER,
    Profile,
    check_file,
    check_img_size,
    check_imshow,
    check_requirements,
    colorstr,
    cv2,
    increment_path,
    non_max_suppression,
    print_args,
    scale_boxes,
    strip_optimizer,
    xyxy2xywh,
)
from utils.torch_utils import select_device, smart_inference_mode

os.environ['KMP_DUPLICATE_LIB_OK']='True'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
@smart_inference_mode()
def run(
    weights=ROOT / "best.pt",  # model path or triton URL
    source=ROOT / "data/images",  # file/dir/URL/glob/screen/0(webcam)
    data=ROOT / "data/widerface.yaml",  # dataset.yaml path
    imgsz=(640, 640),  # inference size (height, width)
    conf_thres=0.25,  # confidence threshold
    iou_thres=0.45,  # NMS IOU  threshold
    max_det=1000,  # maximum detections per image
    device="",  # cuda device, i.e. 0 or 0,1,2,3 or cpu
    view_img=False,  # show results
    save_txt=False,  # save results to *.txt
    save_csv=False,  # save results in CSV format
    save_conf=False,  # save confidences in --save-txt labels
    save_crop=False,  # save cropped prediction boxes
    nosave=False,  # do not save images/videos
    classes=None,  # filter by class: --class 0, or --class 0 2 3
    agnostic_nms=False,  # class-agnostic NMS
    augment=False,  # augmented inference
    visualize=False,  # visualize features
    update=False,  # update all models
    project=ROOT / "runs/detect",  # save results to project/name
    name="exp",  # save results to project/name
    exist_ok=False,  # existing project/name ok, do not increment
    line_thickness=3,  # bounding box thickness (pixels)
    hide_labels=False,  # hide labels
    hide_conf=False,  # hide confidences
    half=False,  # use FP16 half-precision inference
    dnn=False,  # use OpenCV DNN for ONNX inference
    vid_stride=1,  # video frame-rate stride
    ratio= 50,
    reference = "reference_face.jpg",
    carNumber=False,
    face=False,
    knife=False,
    cigar = False
):
    source = str(source) # source는 이미지, 비디오, 웹캠 등의 입력 소스를 나타내는 변수
    save_img = not nosave and not source.endswith(".txt")  # save inference images 추론 결과 이미지로 저장할 것인지
    is_file = Path(source).suffix[1:] in (IMG_FORMATS + VID_FORMATS) # suffix: pathlib의 파일확장자 다루는 함수
    is_url = source.lower().startswith(("rtsp://", "rtmp://", "http://", "https://"))
    webcam = source.isnumeric() or source.endswith(".streams") or (is_url and not is_file)
    screenshot = source.lower().startswith("screen")
    if is_url and is_file:
        source = check_file(source)  # download , 해당 URL에서 파일을 다운로드하는 함수 -> S3 url로 다운로드 받을 경우에 사용할 수 있겠다!

    # Directories
    save_dir = increment_path(Path(project) / name, exist_ok=exist_ok)  # increment run / 중복 허용 x / project: runs/detect name: exp
    (save_dir / "labels" if save_txt else save_dir).mkdir(parents=True, exist_ok=True)  # make dir 결과 저장 디렉터리와 라벨 디렉터리를 생성합니다.

    # Load model
    device = select_device(device)
    model = DetectMultiBackend(weights, device=device, dnn=dnn, data=data, fp16=half)
    stride, names, pt = model.stride, model.names, model.pt # stride :  객체 탐지 모델의 다운샘플링 비율 -> 이미지의 크기를 줄여서(다운샘플링) 처리
    imgsz = check_img_size(imgsz, s=stride)  # check image size

    # Dataloader -> 입력 데이터의 종류에 따라 웹캠, 스크린샷, 이미지/비디오 경로를 데이터셋으로 로드
    bs = 1  # batch_size
    if webcam:
        view_img = check_imshow(warn=True)
        dataset = LoadStreams(source, img_size=imgsz, stride=stride, auto=pt, vid_stride=vid_stride)
        bs = len(dataset)
    elif screenshot:
        dataset = LoadScreenshots(source, img_size=imgsz, stride=stride, auto=pt)
    else:
        dataset = LoadImages(source, img_size=imgsz, stride=stride, auto=pt, vid_stride=vid_stride)
    vid_path, vid_writer = [None] * bs, [None] * bs

    # Run inference
    model.warmup(imgsz=(1 if pt or model.triton else bs, 3, *imgsz))  # warmup
    seen, windows, dt = 0, [], (Profile(device=device), Profile(device=device), Profile(device=device))
    # seen: 추론한 이미지 수를 카운트하는 변수 windows: 추론 결과를 시각화하기 위한 창을 저장할 리스트 dt: 추론 시간을 측정하기 위한 프로파일러 객체들
    for path, im, im0s, vid_cap, s in dataset:
        with dt[0]:
            im = torch.from_numpy(im).to(model.device)
            im = im.half() if model.fp16 else im.float()  # uint8 to fp16/32
            im /= 255  # 0 - 255 to 0.0 - 1.0 픽셀 정규화 작업
            if len(im.shape) == 3:
                im = im[None]  # expand for batch dim
            if model.xml and im.shape[0] > 1:
                ims = torch.chunk(im, im.shape[0], 0)

        # Inference
        with dt[1]: # dt[1]은 추론 시간을 측정하기 위한 프로파일러
            visualize = increment_path(save_dir / Path(path).stem, mkdir=True) if visualize else False
            # OpenVINO XML 모델이고 배치 크기가 1 이상일 때 동작합니다. 배치 내의 각 이미지에 대해 개별적으로 추론을 수행하고, 결과를 pred에 누적합니다. augment는 데이터 augmentation 여부, visualize는 시각화 여부를 결정
            if model.xml and im.shape[0] > 1:
                pred = None
                for image in ims:
                    if pred is None:
                        pred = model(image, augment=augment, visualize=visualize).unsqueeze(0)
                    else:
                        pred = torch.cat((pred, model(image, augment=augment, visualize=visualize).unsqueeze(0)), dim=0)
                pred = [pred, None]
            # 그 외의 경우에는 im 텐서를 직접 모델에 입력하여 추론을 수행
            else:
                pred = model(im, augment=augment, visualize=visualize)
            # 결과를 pred에 저장
        # NMS
        with dt[2]:
            pred = non_max_suppression(pred, conf_thres, iou_thres, classes, agnostic_nms, max_det=max_det)

        # Second-stage classifier (optional)
        # pred = utils.general.apply_classifier(pred, classifier_model, im, im0s)

        # Define the path for the CSV file
        csv_path = save_dir / "predictions.csv"

        # Create or append to the CSV file : csv 파일에 이미지와 정확도 등등을 기록
        def write_to_csv(image_name, prediction, confidence):
            """Writes prediction data for an image to a CSV file, appending if the file exists."""
            data = {"Image Name": image_name, "Prediction": prediction, "Confidence": confidence}
            with open(csv_path, mode="a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=data.keys())
                if not csv_path.is_file():
                    writer.writeheader()
                writer.writerow(data)

        # Process predictions
        # pred 리스트에서 하나씩 객체 탐지 결과(det)를 가져와 처리
        # enumerate를 사용하여 인덱스(i)와 값(det)을 동시에 가져옵니다
        start = time.time()

        for i, det in enumerate(pred):  # per image
            seen += 1
            if webcam:  # batch_size >= 1
                # path[i]는 현재 이미지의 경로, im0s[i]는 원본 이미지, s는 출력 문자열이며, 여기에 인덱스를 추가
                p, im0, frame = path[i], im0s[i].copy(), dataset.count
                s += f"{i}: "
            else:
                # im0s는 원본 이미지 리스트
                p, im0, frame = path, im0s.copy(), getattr(dataset, "frame", 0)
            
            p = Path(p)  # to Path
            # 결과 저장 경로(save_path)와 텍스트 파일 경로(txt_path) 
            # 텍스트 파일 이름에는 frame 번호가 추가됨
            save_path = str(save_dir / p.name)  # im.jpg
            txt_path = str(save_dir / "labels" / p.stem) + ("" if dataset.mode == "image" else f"_{frame}")  # im.txt
            s += "%gx%g " % im.shape[2:]  # print string
            gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  # normalization gain whwh
            imc = im0.copy() if save_crop else im0  # for save_crop
            # 이미지에 "바운딩 박스"와 "레이블"을 그리기 위한 Annotator 객체도 생성
            annotator = Annotator(im0, line_width=line_thickness, example=str(names))

            # 객체 탐지 결과를 후처리하고 출력하는 과정, len(det) -> det이 안비어있을 경우에 
            if len(det):
                # Rescale boxes from img_size to im0 size
                det[:, :4] = scale_boxes(im.shape[2:], det[:, :4], im0.shape).round()

                # Print results
                for c in det[:, 5].unique():
                    n = (det[:, 5] == c).sum()  # detections per class
                    s += f"{n} {names[int(c)]}{'s' * (n > 1)}, "  # add to string

                # 모자이크 처리 제외 reference_path
                reference_path = reference
                print(reference_path)

                # Write results
                # 각 객체의 바운딩 박스 좌표(xyxy), 신뢰도(conf), 클래스(cls)를 가져옵니다.
                for *xyxy, conf, cls in reversed(det):
                    c = int(cls)  # integer class
                    label = names[c] if hide_conf else f"{names[c]}"
                    confidence = float(conf)
                    confidence_str = f"{confidence:.2f}"

                    if save_csv:
                        write_to_csv(p.name, label, confidence_str)

                    if save_txt:  # Write to file
                        xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()  # normalized xywh
                        line = (cls, *xywh, conf) if save_conf else (cls, *xywh)  # label format
                        with open(f"{txt_path}.txt", "a") as f:
                            f.write(("%g " * len(line)).rstrip() % line + "\n")

                    if save_img or save_crop or view_img:  # Add bbox to image
                        c = int(cls)  # integer class
                        if names[c] == 'cigar':
                            if cigar:
                                x1, y1, x2, y2 = map(int, xyxy)
                                roi = im0[y1:y2, x1:x2]
                                roi = cv2.resize(roi, (0, 0), fx=5/ratio, fy=5/ratio)  # 모자이크 처리할 영역 축소
                                roi = cv2.resize(roi, (x2 - x1, y2 - y1), interpolation=cv2.INTER_NEAREST)  # 원래 크기로 확대
                                im0[y1:y2, x1:x2] = roi

                        if names[c] == 'licensePlate':
                            if carNumber:
                                x1, y1, x2, y2 = map(int, xyxy)
                                roi = im0[y1:y2, x1:x2]
                                roi = cv2.resize(roi, (0, 0), fx=5/ratio, fy=5/ratio)  # 모자이크 처리할 영역 축소
                                roi = cv2.resize(roi, (x2 - x1, y2 - y1), interpolation=cv2.INTER_NEAREST)  # 원래 크기로 확대
                                im0[y1:y2, x1:x2] = roi

                        if names[c] == 'knife':
                            if knife:
                                x1, y1, x2, y2 = map(int, xyxy)
                                roi = im0[y1:y2, x1:x2]
                                roi = cv2.resize(roi, (0, 0), fx=5/ratio, fy=5/ratio)  # 모자이크 처리할 영역 축소
                                roi = cv2.resize(roi, (x2 - x1, y2 - y1), interpolation=cv2.INTER_NEAREST)  # 원래 크기로 확대
                                im0[y1:y2, x1:x2] = roi

                        if names[c] == 'face':
                            # bounding box 좌표 추출
                            # 탐지된 객체의 바운딩 박스 좌표(xyxy)를 정수형으로 변환하여 x1, y1, x2, y2에 저장합니다. 그리고 원본 이미지(im0)에서 해당 영역(roi)을 추출합니다.
                            if face:
                                x1, y1, x2, y2 = map(int, xyxy)
                                face0 = im0[y1:y2, x1:x2]

                                face_array = np.array(face0)
                                if allowed_file(reference_path):
                                    try:
                                        result = DeepFace.verify(
                                            img1_path= reference_path,
                                            img2_path= face_array,
                                            enforce_detection=False,
                                        )
                                        print("얼굴 비교 시도")
                                        if not result['verified']:
                                            # reference_face가 없는 경우 모든 얼굴 모자이크 처리
                                            roi = im0[y1:y2, x1:x2]
                                            # 모자이크 처리 -> 0.05일때 진했음(작을수록 진해짐)
                                            roi = cv2.resize(roi, (0, 0), fx=5/ratio, fy=5/ratio)  # 모자이크 처리할 영역 축소
                                            roi = cv2.resize(roi, (x2 - x1, y2 - y1), interpolation=cv2.INTER_NEAREST)  # 원래 크기로 확대
                                            # 모자이크 적용
                                            # 원본 이미지(im0)의 해당 영역에 모자이크 처리된 roi를 대입
                                            im0[y1:y2, x1:x2] = roi
                                    except ValueError as e:
                                        print(f"Error comparing reference face: {e}")
                                else:
                                    print("그냥 모자이크 처리")
                                    roi = im0[y1:y2, x1:x2]
                                    roi = cv2.resize(roi, (0, 0), fx=5/ratio, fy=5/ratio)  # 모자이크 처리할 영역 축소
                                    roi = cv2.resize(roi, (x2 - x1, y2 - y1), interpolation=cv2.INTER_NEAREST)  # 원래 크기로 확대
                                    im0[y1:y2, x1:x2] = roi
                        # else:
                        #     print("그냥 모자이크 처리")
                        #     roi = im0[y1:y2, x1:x2]
                        #     roi = cv2.resize(roi, (0, 0), fx=5/ratio, fy=5/ratio)  # 모자이크 처리할 영역 축소
                        #     roi = cv2.resize(roi, (x2 - x1, y2 - y1), interpolation=cv2.INTER_NEAREST)  # 원래 크기로 확대
                        #     im0[y1:y2, x1:x2] = roi
                        # else:
                            # 그리고 hide_labels와 hide_conf 옵션에 따라 출력할 레이블 텍스트를 결정
                            # label = None if hide_labels else (names[c] if hide_conf else f"{names[c]} {conf:.2f}")
                            # xyxy는 바운딩 박스 좌표, label은 레이블 텍스트, colors는 클래스별 색상을 결정하는 함수입니다.
                            # annotator.box_label(xyxy, label, color=colors(c, True))
                    if save_crop:
                        save_one_box(xyxy, imc, file=save_dir / "crops" / names[c] / f"{p.stem}.jpg", BGR=True)
                        #save_crop 옵션이 True이면, save_one_box 함수를 호출하여 잘린 객체 이미지를 저장합니다. xyxy는 바운딩 박스 좌표, imc는 원본 이미지의 복사본입니다. 저장 경로는 save_dir/crops/클래스이름/파일이름.jpg입니다. BGR=True는 OpenCV의 BGR 색상 포맷을 사용한다는 의미

            # Stream results
            # im0 = annotator.result() # YOLOv5 모델의 결과를 이미지로 반환하는 메서드
            if view_img:
                if platform.system() == "Linux" and p not in windows: # 리눅스 환경 이미지 출력
                    windows.append(p)
                    cv2.namedWindow(str(p), cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)  # allow window resize (Linux)
                    cv2.resizeWindow(str(p), im0.shape[1], im0.shape[0])
                cv2.imshow(str(p), im0)
                cv2.waitKey(1)  # 1 millisecond

            # Save results (image with detections)
            if save_img:
                if dataset.mode == "image": # 이미지 im0를 save_path에 저장
                    cv2.imwrite(save_path, im0)
                else:  # 'video' or 'stream'
                    if vid_path[i] != save_path:  # vid_path[i]가 save_path와 다르면 새로운 비디오 파일을 여는 것
                        vid_path[i] = save_path   
                        if isinstance(vid_writer[i], cv2.VideoWriter):
                            vid_writer[i].release()  # 이전에 열린 vid_writer[i]가 있다면 해제
                        if vid_cap:  # video이면 vid_cap에서 FPS, 가로 해상도, 세로 해상도를 가져옵니다.
                            fps = vid_cap.get(cv2.CAP_PROP_FPS)
                            w = int(vid_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                            h = int(vid_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                            # 비트레이트 설정
                            # bitrate = vid_cap.get(cv2.CAP_PROP_BITRATE)
                        else:  # stream
                            fps, w, h = 30, im0.shape[1], im0.shape[0]
                        save_path = str(Path(save_path).with_suffix(".mp4"))  # force *.mp4 suffix on results videos 코덱 -> 코덱의 종류가 다를 경우 문제가 될 수 있음. 찾아봐야함.
                        vid_writer[i] = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
                    vid_writer[i].write(im0)

        # Print time (inference-only)
        LOGGER.info(f"{s}{'' if len(det) else '(no detections), '}{dt[1].dt * 1E3:.1f}ms")
    end = time.time()
    print(f"{end - start:.5f} sec")
    # Print results
    # dt: 시간 측정값들의 리스트
    t = tuple(x.t / seen * 1e3 for x in dt)  # x.t / seen * 1e3는 각 이미지당 걸린 시간을 밀리초 단위로 변환
    # t는 전처리, 추론, NMS 시간의 튜플로 저장
    LOGGER.info(f"Speed: %.1fms pre-process, %.1fms inference, %.1fms NMS per image at shape {(1, 3, *imgsz)}" % t)
    if save_txt or save_img:
        s = f"\n{len(list(save_dir.glob('labels/*.txt')))} labels saved to {save_dir / 'labels'}" if save_txt else ""
        LOGGER.info(f"Results saved to {colorstr('bold', save_dir)}{s}")
    if update:
        strip_optimizer(weights[0])  # update model (to fix SourceChangeWarning)


def parse_opt():
    """Parses command-line arguments for YOLOv5 detection, setting inference options and model configurations."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", nargs="+", type=str, default=ROOT / "best.pt", help="model path or triton URL")
    parser.add_argument("--source", type=str, default=ROOT / "data/images", help="file/dir/URL/glob/screen/0(webcam)")
    parser.add_argument("--data", type=str, default=ROOT / "data/widerface.yaml", help="(optional) dataset.yaml path")
    parser.add_argument("--imgsz", "--img", "--img-size", nargs="+", type=int, default=[640], help="inference size h,w")
    parser.add_argument("--conf-thres", type=float, default=0.25, help="confidence threshold")
    parser.add_argument("--iou-thres", type=float, default=0.45, help="NMS IoU threshold")
    parser.add_argument("--max-det", type=int, default=1000, help="maximum detections per image")
    parser.add_argument("--device", default="", help="cuda device, i.e. 0 or 0,1,2,3 or cpu")
    parser.add_argument("--view-img", action="store_true", help="show results")
    parser.add_argument("--save-txt", action="store_true", help="save results to *.txt")
    parser.add_argument("--save-csv", action="store_true", help="save results in CSV format")
    parser.add_argument("--save-conf", action="store_true", help="save confidences in --save-txt labels")
    parser.add_argument("--save-crop", action="store_true", help="save cropped prediction boxes")
    parser.add_argument("--nosave", action="store_true", help="do not save images/videos")
    parser.add_argument("--classes", nargs="+", type=int, help="filter by class: --classes 0, or --classes 0 2 3")
    parser.add_argument("--agnostic-nms", action="store_true", help="class-agnostic NMS")
    parser.add_argument("--augment", action="store_true", help="augmented inference")
    parser.add_argument("--visualize", action="store_true", help="visualize features")
    parser.add_argument("--update", action="store_true", help="update all models")
    parser.add_argument("--project", default=ROOT / "runs/detect", help="save results to project/name") # 추론 결과 저장 경로
    parser.add_argument("--name", default="exp", help="save results to project/name") 
    parser.add_argument("--exist-ok", action="store_true", help="existing project/name ok, do not increment") # --exist-ok 인수의 목적은 프로그램이 기존 프로젝트 또는 파일 이름을 사용할 수 있도록 허용하는 것
    parser.add_argument("--line-thickness", default=3, type=int, help="bounding box thickness (pixels)")
    parser.add_argument("--hide-labels", default=False, action="store_true", help="hide labels")
    parser.add_argument("--hide-conf", default=False, action="store_true", help="hide confidences")
    parser.add_argument("--half", action="store_true", help="use FP16 half-precision inference")
    parser.add_argument("--dnn", action="store_true", help="use OpenCV DNN for ONNX inference")
    parser.add_argument("--vid-stride", type=int, default=1, help="video frame-rate stride")
    parser.add_argument('--ratio', type=int, default=50, help='multiple ratio to mosaic_ratio')
    parser.add_argument("--reference", type=str, help="reference face image path")
    parser.add_argument("--carNumber", default=False, help="mosaic options")
    parser.add_argument("--face", default=False, help="mosaic options")
    parser.add_argument("--knife", default=False, help="mosaic options")
    parser.add_argument("--cigar", default=False, help="mosaic options")


    opt = parser.parse_args()
    opt.imgsz *= 2 if len(opt.imgsz) == 1 else 1  # expand
    print_args(vars(opt))
    return opt


def main(opt):
    """Executes YOLOv5 model inference with given options, checking requirements before running the model."""
    check_requirements(ROOT / "requirements.txt", exclude=("tensorboard", "thop"))
    run(**vars(opt))


if __name__ == "__main__":
    opt = parse_opt()
    main(opt)
