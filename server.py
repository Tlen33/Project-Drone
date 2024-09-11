from flask import Flask, render_template, jsonify, request, Response
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import cv2
import numpy as np
import time
import logging
import requests
from pyinstrument import Profiler

app = Flask(__name__)
stop_flag = False

# Конфигурируем секретный ключ для JWT
app.config['SECRET_KEY'] = 'my_secret_key'
jwt = JWTManager(app)

# Простое хранилище токенов для авторизованных пользователей
user_tokens = {}

# Инициализируем состояние дрона
drone_state = {
    "id": 1,
    "name": "Stalker-13",
    "status": "landed",  # Статус дрона: "landed" или "flying"
    "mission": "None",   # Текущая миссия: None, "recon" или "patrol"
    "position": {"latitude": 0.0, "longitude": 0.0, "altitude": 0.0},  # Позиция дрона
    "telemetry_data": []  # Телеметрические данные
}

# Пользователи для авторизации
users = {"drone_operator": "password123"}

# Переменные для хранения видео
video_frame = None
fps = 10
quality = 80

# Маршрут для авторизации
@app.route("/login", methods=["POST"])
def login():
    username = request.json.get("username")
    password = request.json.get("password")

    # Проверка правильности введённых данных
    if username in users and users[username] == password:
        # Генерация JWT токена
        token = create_access_token(identity=username)
        user_tokens[username] = token  # Сохраняем токен для пользователя
        return jsonify({"token": token}), 200
    else:
        return jsonify({"error": "Неверный логин или пароль"}), 401

# Маршрут для взлета дрона
@app.route("/takeoff", methods=["POST"])
@jwt_required()
def takeoff():
    profiler.stop()
    profiler.print()
    while not stop_flag:
        try:
            response = requests.post('http://127.0.0.1:5001/takeoff', json={"altitude": 100})
            if response.status_code == 200:
                telemetry_data = response.json()
                return jsonify(telemetry_data), 200
            else:
                return jsonify({"error": "Ошибка при взлете"}), response.status_code
        except Exception as e:
            return jsonify({"error": f"Не удалось подключиться к дрону: {str(e)}"}), 500
    profiler.stop()
    profiler.print()

# Маршрут для посадки дрона
@app.route("/land", methods=["POST"])
@jwt_required()
def land():
    try:
        response = requests.post('http://127.0.0.1:5001/land')
        if response.status_code == 200:
            telemetry_data = response.json()
            return jsonify(telemetry_data), 200
        else:
            return jsonify({"error": "Ошибка при приземлении"}), response.status_code
    except Exception as e:
        return jsonify({"error": f"Не удалось подключиться к дрону: {str(e)}"}), 500

# Маршрут для выполнения миссии разведки
@app.route("/recon", methods=["POST"])
@jwt_required()
def recon_mission():
    if drone_state["mission"] == "recon":
        return jsonify({"error": "Дрон уже выполняет миссию разведки"}), 400

    drone_state["mission"] = "recon"
    logging.info("Дрон начал миссию разведки")
    return jsonify({"message": "Миссия разведки началась", "drone_state": drone_state}), 200

# Маршрут для выполнения миссии патрулирования
@app.route("/patrol", methods=["POST"])
@jwt_required()
def patrol_mission():
    if drone_state["mission"] == "patrol":
        return jsonify({"error": "Дрон уже выполняет миссию патрулирования"}), 400

    drone_state["mission"] = "patrol"
    logging.info("Дрон начал миссию патрулирования")
    return jsonify({"message": "Миссия патрулирования началась", "drone_state": drone_state}), 200

# Маршрут для обновления позиции дрона
@app.route("/update_position", methods=["POST"])
@jwt_required()
def update_position():
    data = request.json
    if not data:
        return jsonify({"error": "Некорректные данные"}), 400

    drone_state["position"]["latitude"] = float(data["latitude"])
    drone_state["position"]["longitude"] = float(data["longitude"])
    drone_state["position"]["altitude"] = float(data["altitude"])
    return jsonify({"message": "Позиция дрона обновлена", "drone_state": drone_state}), 200


# Запрашиваем телеметрию у дрона
@app.route("/get_drone_telemetry", methods=["GET"])
@jwt_required()
def get_drone_telemetry():
    try:
        # Замените 'drone_ip_address' на фактический IP-адрес дрона
        response = requests.get('http://127.0.0.1:5001/telemetry')  # Укажите правильный IP дрона

        if response.status_code == 200:
            telemetry_data = response.json()
            return jsonify(telemetry_data), 200
        else:
            return jsonify({"error": "Ошибка при получении данных от дрона"}), response.status_code

    except Exception as e:
        return jsonify({"error": f"Не удалось подключиться к дрону: {str(e)}"}), 500


# Маршрут для отображения телеметрии
@app.route("/display", methods=["GET"])
@jwt_required()
def display_telemetry():
    return jsonify(drone_state["telemetry_data"]), 200

# Маршрут для приёма и хранения видеопотока с дрона
@app.route("/video", methods=["POST"])
def receive_video():
    global video_frame
    np_array = np.frombuffer(request.data, dtype=np.uint8)
    video_frame = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
    return "", 204

# Маршрут для отображения видеопотока с дрона
@app.route("/video_feed")
def video_feed():
    def generate():
        global video_frame
        while True:
            if video_frame is not None:
                _, buffer = cv2.imencode('.jpg', video_frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(1 / fps)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Маршрут для отображения web-интерфейса
@app.route("/")
def index():
    return render_template("index.html")

# Запуск сервера
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True)
