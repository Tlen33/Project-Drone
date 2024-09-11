import requests
from flask import Flask, jsonify, request
import websockets
import asyncio
import logging
from threading import Thread
from pyinstrument import Profiler

app = Flask(__name__)
stop_flag = False

# Пример телеметрических данных дрона
drone_telemetry = {
    "latitude": 55.7558,
    "longitude": 37.6173,
    "altitude": 0.0,  # Начальная высота 0
    "battery": 85,
    "speed": 0.0  # Начальная скорость 0
}

# Маршрут для передачи телеметрии дрона
@app.route("/telemetry", methods=["GET"])
def send_telemetry():
    return jsonify(drone_telemetry), 200

# Маршрут для взлета дрона
@app.route("/takeoff", methods=["POST"])
def takeoff():
    profiler.stop()
    profiler.print()
    while not stop_flag:
        altitude = request.json.get('altitude', 100)  # Высота по умолчанию 100 метров
        drone_telemetry["altitude"] = altitude  # Обновляем высоту в телеметрии
        drone_telemetry["speed"] = 10.0  # Пример изменения скорости при взлете
        logging.info(f"Дрон взлетает на высоту: {altitude} метров")
        return jsonify({"message": f"Взлет на {altitude} метров выполнен", "drone_telemetry": drone_telemetry}), 200
    profiler.stop()
    profiler.print()

# Маршрут для посадки дрона
@app.route("/land", methods=["POST"])
def land():
    drone_telemetry["altitude"] = 0.0  # При посадке высота 0
    drone_telemetry["speed"] = 0.0  # Пример изменения скорости на 0 при посадке
    logging.info("Дрон приземляется")
    return jsonify({"message": "Посадка выполнена", "drone_telemetry": drone_telemetry}), 200

# Запуск Flask-сервера в отдельном потоке
def start_flask_server():
    app.run(host="0.0.0.0", port=5001, debug=True, use_reloader=False)

# Функция для управления дроном через WebSocket
async def control_drone(websocket, path):
    async for message in websocket:
        logging.info(f"Получена команда: {message}")
        if message == "takeoff":
            drone_telemetry["altitude"] = 100.0  # Пример взлета через WebSocket
            drone_telemetry["speed"] = 10.0
            logging.info("Дрон взлетает")
            await websocket.send("Дрон взлетает")
        elif message == "land":
            drone_telemetry["altitude"] = 0.0  # Пример посадки через WebSocket
            drone_telemetry["speed"] = 0.0
            logging.info("Дрон приземляется")
            await websocket.send("Дрон приземляется")

# Функция для запуска WebSocket-сервера
async def start_websocket_server():
    async with websockets.serve(control_drone, "127.0.0.1", 8765):
        logging.info("WebSocket сервер запущен")
        await asyncio.Future()  # Блокируем выполнение, чтобы сервер продолжал работать

# Запуск WebSocket-сервера в основном потоке
def start_websocket():
    asyncio.run(start_websocket_server())

if __name__ == "__main__":
    # Запускаем Flask-сервер в отдельном потоке
    flask_thread = Thread(target=start_flask_server)
    flask_thread.start()
    logging.basicConfig(level=logging.INFO)

    # Запускаем WebSocket-сервер в основном потоке
    start_websocket()
