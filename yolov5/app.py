from flask import Flask, request, render_template
import cv2
import numpy as np
import torch
import shutil
import os
from datetime import datetime
app = Flask(__name__)

# # YOLOv5 모델 로드
# model = torch.hub.load('ultralytics/yolov5', 'yolov5s', force_reload=True)

# 업로드된 파일이 저장될 디렉토리 경로
UPLOAD_FOLDER = 'uploads'
video_folder = "video_uploads"
reference_folder = 'reference'
# 허용할 파일 확장자
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov'}
detect_folder =""
# 파일 확장자를 체크하는 함수
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    # in -> 특정 값이 시퀀스(리스트, 튜플, 문자열 등) 안에 속하는지 여부를 확인
    # and -> 두 개의 조건이 모두 참(True)일 때 전체 표현식이 참
    # .rsplit() -> 문자열을 오른쪽부터 지정된 구분자를 기준으로 분할하는 메서드

# 이미지 파일을 바이트 스트림으로 읽어와 반환하는 함수
def read_image(file_path):
    with open(file_path, 'rb') as file :
        image_bytes = file.read()
    return image_bytes

# 홈페이지 라우트
@app.route('/')
def home():
    return render_template('index.html')

reference_face_path = "data/reference_face.jpg"
# 이미지 업로드 라우트
@app.route('/detect', methods=['POST'])
def upload_file():
    detect_folder =""
    # 파일이 업로드 되었는지 확인
    if 'file' not in request.files:
        return 'No file part'
    
    file = request.files['file']
    ratio = request.form['ratio']

    print(type(ratio))
    print(ratio)

    # 파일이 비어 있는지 확인
    if file.filename == '':
        return 'No selected file'
    
    # 파일이 허용된 확장자인지 확인(file이 비어있으면 false AND 확장자가 올바르지 않으면 false)
    if file and allowed_file(file.filename):
        # 파일을 업로드할 디렉토리 생성(increment 로직 추가 필요)
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
        
        # 파일을 저장할 경로 설정
        # os.path.join : 인수에 전달된 2개의 문자열을 결합하여, 1개의 경로로 할 수 있다. 인자 사이에는 /가 포함됨.
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        
        # 파일 저장
        file.save(filepath)
        
        # 모자이크할 이미지 저장된 경로
        dir_path= filepath
        # terminal 명령어 파이썬 내에서 실행
        # os.system(f'copy "{filepath}" "{os.path.join(UPLOAD_FOLDER, "hello2.jpg")}"')
        # python detect.py --weights yolov5s.pt --img 640 --conf 0.25 --source data/images/zidane.jpg
        os.system(f'python detect.py --weights best.pt --img 640 --conf 0.25 --source "{dir_path}" --ratio {ratio} --reference "{reference_face_path}"')


        # 기존에 생성된 exp 폴더의 번호 중 가장 큰 번호 찾기
        exp_folders = [f.path for f in os.scandir("runs/detect") if f.is_dir() and f.name.startswith('exp')]

        # 폴더 생성 시간으로 정렬
        exp_folders.sort(key=lambda x: os.path.getmtime(x), reverse=True)

        # 가장 최근 폴더 경로 할당
        if exp_folders:
            detect_folder = exp_folders[0]
            print(f"detect-folder: {detect_folder}")
        else:
            print("'exp' 로 시작하는 폴더가 없습니다.")

        detect_path = os.path.join(detect_folder, file.filename)
        return read_image(detect_path)
    else:
        return 'Allowed file types are png, jpg, jpeg, gif'

# 비디오 파일 처리를 위한 라우트 추가
@app.route('/detect_video', methods=['POST'])
def upload_video():
    detect_folder = ""
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    ratio = request.form['ratio']

    if file.filename == '':
        return 'No selected file'

    if file and allowed_file(file.filename):
        if not os.path.exists(video_folder):
            os.makedirs(video_folder)

        filepath = os.path.join(video_folder, file.filename)
        file.save(filepath)
        video_path = filepath

        os.system(f'python detect.py --weights best.pt --img 640 --conf 0.25 --source "{video_path}"')

        exp_folders = [f.path for f in os.scandir("runs/detect") if f.is_dir() and f.name.startswith('exp')]
        exp_folders.sort(key=lambda x: os.path.getmtime(x), reverse=True)

        if exp_folders:
            detect_folder = exp_folders[0]
            print(f"detect-folder: {detect_folder}")
        else:
            print("'exp' 로 시작하는 폴더가 없습니다.")

        detect_path = os.path.join(detect_folder, file.filename)
        return read_image(detect_path)
    else:
        return 'Allowed file types are png, jpg, jpeg, gif, mp4, avi, mov'
if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port= 5000)
