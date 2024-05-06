from flask import Flask, request, render_template
import cv2
import numpy as np
import torch
import shutil
import os
app = Flask(__name__)

# # YOLOv5 모델 로드
# model = torch.hub.load('ultralytics/yolov5', 'yolov5s', force_reload=True)

# 업로드된 파일이 저장될 디렉토리 경로
UPLOAD_FOLDER = 'uploads'
# 허용할 파일 확장자
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# 파일 확장자를 체크하는 함수
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 홈페이지 라우트
@app.route('/')
def home():
    return render_template('index.html')

# 이미지 업로드 라우트
@app.route('/detect', methods=['POST'])
def upload_file():
    # 파일이 업로드 되었는지 확인
    if 'file' not in request.files:
        return 'No file part'
    
    file = request.files['file']

    # 파일이 비어 있는지 확인
    if file.filename == '':
        return 'No selected file'
    
    # 파일이 허용된 확장자인지 확인
    if file and allowed_file(file.filename):
        # 파일을 업로드할 디렉토리 생성
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
        
        # 파일을 저장할 경로 설정
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        
        # 파일 저장
        file.save(filepath)
        
        os.system(f'copy "{filepath}" "{os.path.join(UPLOAD_FOLDER, "hello2.jpg")}"')
        return 'File uploaded successfully'
    else:
        return 'Allowed file types are png, jpg, jpeg, gif'


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port= 5000)