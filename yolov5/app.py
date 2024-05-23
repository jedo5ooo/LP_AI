from flask import Flask, request, render_template
import os
import boto3
import json
from dotenv import load_dotenv
from moviepy.editor import *

load_dotenv()

app = Flask(__name__)
# import cv2
# import numpy as np
# import torch
# import shutil
# from datetime import datetime

# # YOLOv5 모델 로드
# model = torch.hub.load('ultralytics/yolov5', 'yolov5s', force_reload=True)

# 업로드된 파일이 저장될 디렉토리 경로
upload_folder = 'uploads'
croped_folder = 'croped'
video_folder = "video_uploads"
# 허용할 파일 확장자
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov'}
detect_folder =""

# S3 클라이언트 생성
s3 = boto3.client('s3', 
                  aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                  aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))
bucket_name = os.getenv('AWS_S3_BUCKET_NAME')

def download_file_from_s3(file_name, destination_folder):
    s3.download_file(bucket_name, file_name, os.path.join(destination_folder, file_name))

def upload_file_to_s3(file_path, file_name):
    s3.upload_file(file_path, bucket_name, file_name)

# 파일 확장자를 체크하는 함수
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    # in -> 특정 값이 시퀀스(리스트, 튜플, 문자열 등) 안에 속하는지 여부를 확인
    # and -> 두 개의 조건이 모두 참(True)일 때 전체 표현식이 참
    # .rsplit() -> 문자열을 오른쪽부터 지정된 구분자를 기준으로 분할하는 메서드

def get_file_type(filename):
    return '.' + filename.rsplit('.', 1)[1].lower()

def get_file_name(filename):
    return filename.rsplit('.',1)[0].lower()

# 이미지 파일을 바이트 스트림으로 읽어와 반환하는 함수
def read_image(file_path):
    with open(file_path, 'rb') as file :
        image_bytes = file.read()
    return image_bytes

saved_name = ""
file_size = ""
file_type = ""
file_name = ""
# 홈페이지 라우트
# @app.route('/')
# def home():
#     return render_template('index.html')
# 이미지 업로드 라우트
@app.route('/detect', methods=['POST'])
def mosaic_file():
    detect_folder =""
    get_data = request.get_json()
    file_name = get_data['original']['original_file_name']
    print(file_name)
    croped_file_name = ""
    try:
        croped_file_name = get_data['area']['area_0_file_name']
        print(croped_file_name)
    except:
        print("예외처리할 대상 없음.")

    # 모자이크 옵션 딕셔너리 생성
    ratio = get_data['data']['intensityAuto']
    carNumber = get_data['data']['carNumber']
    carNumber = True if carNumber.lower() == "true" else False
    face = get_data['data']['face']
    face = True if face.lower() == "true" else False
    print(face)
    knife = get_data['data']['knife']
    knife = True if knife.lower() == "true" else False
    print(knife)
    cigar = get_data['data']['cigar']
    cigar = True if cigar.lower() == "true" else False
    
    # 파일이 비어 있는지 확인
    if file_name == '':
        return 'No file name provided'
    
    # 파일이 허용된 확장자인지 확인(file이 비어있으면 false AND 확장자가 올바르지 않으면 false)
    if allowed_file(file_name):
        # 파일을 업로드할 디렉토리 생성(increment 로직 추가 필요)
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        
        if not os.path.exists(croped_folder):
            os.makedirs(croped_folder)
        # 파일을 저장할 경로 설정
        # os.path.join : 인수에 전달된 2개의 문자열을 결합하여, 1개의 경로로 할 수 있다. 인자 사이에는 /가 포함됨.
        filepath = os.path.join(upload_folder, file_name)
        try:
            croped_path = os.path.join(croped_folder, croped_file_name)
            print("S3에서 가져온 이름 + 폴더명"+croped_path)
        except: 
            print('croped가 None이라 붙일 수 없음.')

        # S3에서 파일 다운로드
        download_file_from_s3(file_name, upload_folder)
        try:
            download_file_from_s3(croped_file_name, croped_folder)
        except:
            print("다운로드할 이미지 없음.")
        # 모자이크할 이미지 저장된 경로
        dir_path= filepath

        # terminal 명령어 파이썬 내에서 실행
        os.system(f'python detect.py --weights 4class.pt --img 640 --conf 0.25 --source "{dir_path}" --ratio {ratio} --carNumber "{carNumber}" --face "{face}" --knife "{knife}" --cigar "{cigar}" --reference "{croped_path}" ')


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

        detect_path = os.path.join(detect_folder, file_name)

        # 모자이크 처리된 파일의 확장자 확인
        _, ext = os.path.splitext(file_name)
        if ext.lower() in ['.mp4', '.mov', '.avi']:
            # 모자이크 처리된 동영상 파일 로드
            resultVideo = VideoFileClip(detect_path)

            # 원본 동영상 파일 로드
            audioVideo = VideoFileClip(filepath)

            # 원본 동영상에서 오디오 추출
            audio = audioVideo.audio

            # 모자이크 처리된 동영상에 오디오 합치기
            video = resultVideo.set_audio(audio)

            # 합쳐진 동영상 파일 저장
            output_path = os.path.join(detect_folder, f"mosaic_{file_name}")
            video.write_videofile(output_path, fps=video.fps)

            saved_name = f"mosaic_{file_name}"
        else: 
            output_path = os.path.join(detect_folder, file_name)    
            saved_name = f"mosaic_{file_name}"

        # 모자이크 처리된 파일을 S3에 업로드  
        file_size = os.path.getsize(output_path)
        file_type = get_file_type(saved_name)
        upload_file_to_s3(output_path, f"{saved_name}")

        # SpringBoot로 json type으로 S3에 저장된 이름, 확장자명, 파일 사이즈 넘겨주기
        res = {"file_name": f'{saved_name}', "file_size": int(file_size), "file_type": f'{file_type}', "file_rename": f'{saved_name}'}
        print(res)
        return res
    else:
        return 'Allowed file types are png, jpg, jpeg, gif'
# 받은 이미지들은 다시 끝나면 삭제

# # 비디오 파일 처리를 위한 api 추가
# @app.route('/video_detect', methods=['POST'])
# def mosaic_video():
#     detect_folder = ""
#     file_name = request.form['file_name']
#     ratio = request.form['ratio']

#     if file_name == '':
#         return 'No selected file'

#     if allowed_file(file_name):
#         if not os.path.exists(video_folder):
#             os.makedirs(video_folder)

#         filepath = os.path.join(video_folder, file_name)

#         # S3에서 파일 다운로드
#         download_file_from_s3(file_name, video_folder)

#         video_path = filepath

#         os.system(f'python video_detect.py --weights 4class.pt --img 640 --conf 0.25 --source "{video_path}" --ratio {ratio}')

#         exp_folders = [f.path for f in os.scandir("runs/detect") if f.is_dir() and f.name.startswith('exp')]
#         exp_folders.sort(key=lambda x: os.path.getmtime(x), reverse=True)

#         if exp_folders:
#             detect_folder = exp_folders[0]
#             print(f"detect-folder: {detect_folder}")
#         else:
#             print("'exp' 로 시작하는 폴더가 없습니다.")

#         detect_path = os.path.join(detect_folder, file_name)
    
#         # 모자이크 처리된 파일을 S3에 업로드  
#         saved_name = f"mosaic_{file_name}"
#         file_size = os.path.getsize(detect_path)
#         file_type = get_file_type(saved_name)
#         file_name = get_file_name(saved_name)
#         upload_file_to_s3(detect_path, saved_name)

#         # SpringBoot로 json type으로 S3에 저장된 이름, 확장자명, 파일 사이즈 넘겨주기
#         data = {'file_name': f'{file_name}', 'file_size': f'{file_size}', 'file_type': f'{file_type}'}
#         json.dumps(data)
#         print(data)
#         return data
#     else:
#         return 'Allowed file types are png, jpg, jpeg, gif, mp4, avi, mov'
# if __name__ == '__main__':
#     app.run(debug=True, host='127.0.0.1', port= 5000)
