from flask import Flask, request, render_template
import boto3, json
from werkzeug.utils import secure_filename
from socket import *

app = Flask(__name__)

# !! 주의 route 뒤에 경로는 위에 Spring에서 적은 경로와 같아야함 !!
@app.route('/receive_string', methods=['POST'])
def receive_string():
	#Spring으로부터 JSON 객체를 전달받음
    dto_json = request.get_json()
    
    #dto_json을 dumps 메서드를 사용하여 response에 저장
    response = json.dumps(dto_json, ensure_ascii=False)
	
   	#Spring에서 받은 데이터를 출력해서 확인
    print(dto_json)
    
    #Spring으로 response 전달
    return response

# 0.0.0.0 으로 모든 IP에 대한 연결을 허용해놓고 포트는 5001로 설정
if __name__ == '__main__':
    app.run('0.0.0.0', port=5001, debug=True)