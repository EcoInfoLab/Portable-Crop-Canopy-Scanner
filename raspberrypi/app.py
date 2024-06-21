import os
import cv2
from datetime import datetime
from flask import Flask, request, redirect, render_template_string, jsonify
import json
import time
import requests
import subprocess
from as7262 import AS7262
import csv

app = Flask(__name__)

# min 함수와 max 함수를 Jinja2 템플릿에서 사용할 수 있도록 등록
app.jinja_env.globals.update(min=min, max=max)

# configuration.json에서 설정 읽기
with open('configuration.json') as config_file:
    config = json.load(config_file)

# 초기 위치 설정
position = {'x': 0, 'y': 0}

# AS7262 분광 센서 초기화
as7262 = AS7262()
as7262.set_gain(64)
as7262.set_integration_time(17.857)
as7262.set_measurement_mode(2)
as7262.set_illumination_led(0)  # LED 끄기

# HTML 템플릿
html_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Crane Controller</title>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/toastr.js/latest/toastr.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/toastr.js/latest/toastr.min.js"></script>
</head>
<body>
    <h1>Controller</h1>
    <!-- 추가된 스타일 -->
    <style>
        #crane-area {
            width: {{ config['max_x'] }}px;
            height: {{ config['max_y'] }}px;
            position: relative;
            background-color: #f0f0f0;
            border: 2px solid #000;
        }
        #crane-position {
            width: 10px;
            height: 10px;
            background-color: red;
            position: absolute;
        }
    </style>

    <!-- 크레인 작동 영역과 현재 위치 마커 추가 -->
    <div id="crane-area">
        <div id="crane-position" style="left: {{ max(0, min(position['x'], config['max_x'] - 10)) }}px; top: {{ max(0, min(position['y'], config['max_y'] - 10)) }}px;"></div>
    </div>

    <form id="control-form" action="/command" method="post">
        <button type="button" onclick="sendCommand('up')">Up</button>
        <button type="button" onclick="sendCommand('down')">Down</button>
        <button type="button" onclick="sendCommand('right')">Right</button>
        <button type="button" onclick="sendCommand('left')">Left</button>
    </form>
    <form id="move-to-form" action="/move_to" method="post">
        <input type="text" name="x" placeholder="x coordinate" required>
        <input type="text" name="y" placeholder="y coordinate" required>
        <button type="submit">Move to Coordinate</button>
    </form>
    <button id="auto-move" type="button" onclick="autoMove()">Auto Move</button>
    <p>Current Position: x = {{ position['x'] }}, y = {{ position['y'] }}</p>
    <script>
        function sendCommand(command) {
            $.post('/command', {command: command}, function(data) {
                toastr.options = { "positionClass": "toast-bottom" };
                let message = data.status === "moving" ? 'Moving...' : 'Limited!';
                toastr.info(message); // 이동 시작 시 팝업 표시

                setTimeout(function() {
                    window.location.reload(); // 5초 후 페이지 리로드
                }, 5000); // 클라이언트에서 5초 대기
            });
        }

        function autoMove() {
            $.post('/auto_move', {}, function(data) {
                toastr.options = { "positionClass": "toast-bottom" };
                toastr.info('Starting auto move...'); // 자동 이동 시작 시 팝업 표시
            });
        }
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    return render_template_string(html_template, position=position, config=config)


@app.route('/command', methods=['POST'])
def command():
    command = request.form.get('command')
    status = move(command)
    return jsonify({"status": status})


@app.route('/auto_move', methods=['POST'])
def auto_move():
    for target in config['auto']:
        move_to(target['x'], target['y'])
    return jsonify({"status": "completed"})


@app.route('/move_to', methods=['POST'])
def handle_move_to():
    x = int(request.form['x'])
    y = int(request.form['y'])
    move_to(x, y)
    return redirect('/')


def move(direction):
    global position, config
    initial_position = position.copy()
    scale = config['scale']

    if direction == 'up':
        if position['y'] + scale <= config['max_y']:
            position['y'] += scale
            print(position)
            requests.get(f"http://{config['y_axis_ip']}/up")  # y축 IP로 HTTP 요청 보내기
        else:
            return 'limited'
    elif direction == 'down':
        if position['y'] - scale >= config['min_y']:
            position['y'] -= scale
            print(position)
            requests.get(f"http://{config['y_axis_ip']}/down")  # y축 IP로 HTTP 요청 보내기
        else:
            return 'limited'
    elif direction == 'right':
        if position['x'] + scale <= config['max_x']:
            position['x'] += scale
            print(position)
            requests.get(f"http://{config['x_axis_ip']}/up")  # x축 IP로 HTTP 요청 보내기
        else:
            return 'limited'
    elif direction == 'left':
        if position['x'] - scale >= config['min_x']:
            position['x'] -= scale
            print(position)
            requests.get(f"http://{config['x_axis_ip']}/down")  # x축 IP로 HTTP 요청 보내기
        else:
            return 'limited'
    else:
        return 'error'  # 잘못된 방향

    if position == initial_position:
        return 'limited'  # 위치 변경 없음
    return 'moving'  # 성공적으로 이동


def move_to(target_x, target_y):
    print(f"Moving to target coordinates: x = {target_x}, y = {target_y}")
    scale = config['scale']

    # x 좌표 조정
    while position['x'] != target_x:
        direction = 'right' if position['x'] < target_x else 'left'
        move_result = move(direction)
        print(f"Moving {direction}: New position = x = {position['x']}, y = {position['y']}")
        if move_result == 'limited':
            print("Movement limited. Cannot proceed further in this direction.")
            break  # 이동 제한 시 중단
        time.sleep(5)  # 5초 대기

    # y 좌표 조정
    while position['y'] != target_y:
        direction = 'up' if position['y'] < target_y else 'down'
        move_result = move(direction)
        print(f"Moving {direction}: New position = x = {position['x']}, y = {position['y']}")
        if move_result == 'limited':
            print("Movement limited. Cannot proceed further in this direction.")
            break  # 이동 제한 시 중단
        time.sleep(5)  # 5초 대기

    if position['x'] == target_x and position['y'] == target_y:
        print(f"Arrived at the target position: x = {target_x}, y = {target_y}")
        # USB 카메라로 사진 캡처
        capture_image()
        
        # 열화상 사진 캡처  
        now = datetime.now()
        date_folder = now.strftime("%Y-%m-%d")
        time_folder = now.strftime("%H")
        coordinate = f"{position['x']}_{position['y']}"
        
        # 캡처 폴더 생성
        os.makedirs(f"captures/{date_folder}/{time_folder}/thermal", exist_ok=True)
        
        thermal_filename = f"captures/{date_folder}/{time_folder}/thermal/{coordinate}.png"
        capture_thermal_image(thermal_filename)
        
        # NiR 데이터 캡처
        capture_nir_data()
    else:
        print("Did not arrive at the exact target position due to limitations.")

    return redirect('/')  # 최종 이동 완료 후 페이지 새로 고침


def capture_image():
    cap = cv2.VideoCapture(0)  # 0은 기본 카메라를 의미합니다.
    ret, frame = cap.read()
    cap.release()

    if ret:
        now = datetime.now()
        date_folder = now.strftime("%Y-%m-%d")
        time_folder = now.strftime("%H")
        coordinate = f"{position['x']}_{position['y']}"
        
        # 캡처 폴더 생성
        os.makedirs(f"captures/{date_folder}/{time_folder}/picture", exist_ok=True)
        
        image_filename = f"captures/{date_folder}/{time_folder}/picture/{coordinate}.jpg"
        cv2.imwrite(image_filename, frame)
        print(f"Image captured at {coordinate}")
    else:
        print("Failed to capture image")


def capture_thermal_image(filename):
    try:
        subprocess.run(["sudo", "pylepton_capture", filename], check=True)
        print(f"Thermal image captured: {filename}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to capture thermal image: {e}")


def capture_nir_data():
    values = as7262.get_calibrated_values()
    
    now = datetime.now()
    date_folder = now.strftime("%Y-%m-%d")
    time_folder = now.strftime("%H")
    coordinate = f"{position['x']}_{position['y']}"
    
    # 폴더 생성
    os.makedirs(f"captures/{date_folder}/{time_folder}/NiR", exist_ok=True)
    
    # CSV 파일 경로 생성
    csv_filename = f"captures/{date_folder}/{time_folder}/NiR/{coordinate}.csv"
    
    # CSV 파일 열기 (파일이 없으면 생성)
    with open(csv_filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        
        # 파일이 비어있으면 헤더 행 추가
        if file.tell() == 0:
            writer.writerow(['Date/Time', '610nm', '680nm', '730nm', '760nm', '810nm', '860nm'])
        
        # 현재 시간과 분광 데이터 기록
        current_time = now.strftime("%H:%M:%S.%f")[:-4]  # 마이크로초 단위까지 기록
        writer.writerow([current_time] + list(values))
    
    print("NiR data recorded to", csv_filename)


if __name__ == '__main__':
    app.run(host ="0.0.0.0",debug=False)
