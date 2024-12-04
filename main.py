import secrets
from flask import Flask, request, jsonify, send_file
import io
import base64
import requests
import threading
from apscheduler.schedulers.background import BackgroundScheduler
import time

app = Flask(__name__)

# Hàm tạo token ngẫu nhiên (20 ký tự)
def generate_token(length=20):
    return ''.join(secrets.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(length))

# Danh sách bot lưu trữ tạm thời
# Danh sách bots
bots = {}

# Hàm lấy danh sách bots từ API
def get_token():
    try:
        url = "https://674c570654e1fca9290c42c7.mockapi.io/api_device"
        headers = {
            "Authorization": "674c570654e1fca9290c42c7",
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        users = response.json()

        # Trả về danh sách bots
        return users
    except requests.RequestException as e:
        print(f"Error fetching bots: {e}")
        return []

# Hàm cập nhật bots định kỳ

def update_bots():
    global bots
    try:
        bot_list = get_token()
        bots = {bot['token']: {"name": bot['name']} for bot in bot_list}
        print(f"Bots updated: {bots}")  # Log để kiểm tra cập nhật
    except Exception as e:
        print(f"Error updating bots: {str(e)}")

update_bots()
@app.route('/api/update_bots', methods=['GET'])
def update_bots_api():
    global bots
    try:
        update_bots()
        # bots = {bot['token']: {"name": bot['name']} for bot in bot_list}
        # print(f"Bots updated: {bots}")  # Log để kiểm tra cập nhật
        return jsonify({"message": "Bots updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to update bots: {str(e)}"}), 500

# Tích hợp APScheduler
# scheduler = BackgroundScheduler()
# scheduler.add_job(update_bots, 'interval', seconds=60)  # Cập nhật mỗi 60 giây
# scheduler.start()
# Tạo biến data_store là một dictionary trống để lưu trữ dữ liệu
data_store = {}

@app.route('/api/<token>', methods=['POST'])
def bot_api(token):
    # Kiểm tra token có tồn tại không
    bot = bots.get(token)
    if not bot:
        return jsonify({"error": "Unauthorized: Invalid token"}), 401

    # Xử lý logic của bot
    data = request.json  # Dữ liệu gửi từ bot

    # Tạo lại data_store mỗi lần gửi mới, đảm bảo không lưu trữ lâu dài
    global data_store
    data_store = {}  # Reset data_store mỗi lần gửi

    # Lưu dữ liệu vào dictionary theo token
    if token not in data_store:
        data_store[token] = []
    data_store[token].append(data)

    response = {
        "message": f"Hello {bot['name']} , you sent: {data}",
        "bot_name": bot["name"],
    }

    return jsonify(response), 200

@app.route('/api/tokens', methods=['GET'])
def get_tokens():
    # Trả về danh sách các token hiện có
    return jsonify({"tokens": list(bots.keys())}), 200

# Endpoint để xem dữ liệu đã gửi theo token
@app.route('/api/<token>/data', methods=['GET'])
def get_token_data(token):
    # Kiểm tra token có tồn tại không
    if token not in bots:
        return jsonify({"error": "Unauthorized: Invalid token"}), 401

    # Trả về dữ liệu đã lưu cho token
    token_data = data_store.get(token, [])
    return jsonify({"token": token, "data": token_data}), 200

# Dictionary lưu file tạm (bộ nhớ)
file_store = {}

@app.route('/api/<token>/upload', methods=['POST'])
def upload_file(token):
    # Kiểm tra token
    bot = bots.get(token)
    if not bot:
        return jsonify({"error": "Unauthorized: Invalid token"}), 401

    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected for uploading"}), 400

    # Đọc file vào bộ nhớ tạm
    file_bytes = io.BytesIO(file.read())
    filename = file.filename
    unique_token = generate_token()  # Sinh token duy nhất cho mỗi file

    # Nếu token đã tồn tại, thay thế file cũ
    file_store[unique_token] = {
        "filename": filename,
        "content": file_bytes.getvalue()
    }

    return jsonify({
        "message": f"File uploaded successfully by {bot['name']}",
        "download_token": unique_token
    }), 200

@app.route('/download/<token>', methods=['GET'])
def download_file(token):
    # Kiểm tra token tồn tại
    file_data = file_store.get(token)
    if not file_data:
        return jsonify({"error": "Invalid or expired token"}), 404

    # Trả file về client
    file_bytes = io.BytesIO(file_data['content'])
    file_bytes.seek(0)
    # file_store.clear()
    return send_file(
        file_bytes,
        mimetype='application/octet-stream',
        as_attachment=True,
        download_name=file_data['filename']
    )
@app.route('/api/newdevice', methods=['POST'])
def add_new_devices():
    # Lấy dữ liệu từ yêu cầu
    data = request.json

    # Kiểm tra dữ liệu đầu vào
    if not data or not isinstance(data, list):
        return jsonify({"error": "Invalid request. Expected a list of devices."}), 400

    added_devices = []
    failed_devices = []

    for device in data:
        # Kiểm tra định dạng từng thiết bị
        if 'token' not in device or 'name' not in device:
            failed_devices.append({"error": "Invalid device format.", "device": device})
            continue

        token = device['token']
        name = device['name']

        # Kiểm tra nếu token đã tồn tại
        if token in bots:
            failed_devices.append({"error": "Device with this token already exists.", "device": device})
            continue

        # Thêm thiết bị vào danh sách
        bots[token] = {"name": name}
        added_devices.append({"token": token, "name": name})

    return jsonify({
        "message": "Devices processed.",
        "added_devices": added_devices,
        "failed_devices": failed_devices
    }), 201
@app.route('/api/newdevice/info', methods=['POST'])
def check_device_info():
    # Lấy danh sách token từ yêu cầu
    data = request.json

    # Kiểm tra dữ liệu đầu vào
    if not data or not isinstance(data, list):
        return jsonify({"error": "Invalid request. Expected a list of tokens."}), 400

    results = []

    for token in data:
        if token in bots:
            # Token tồn tại
            results.append({
                "token": token,
                "name": bots[token]["name"],
                "status": "found"
            })
        else:
            # Token không tồn tại
            results.append({
                "token": token,
                "status": "not found"
            })

    return jsonify({"devices": results}), 200

@app.route('/api/<token>/reset_data', methods=['GET'])
def reset_data(token):
    bot = bots.get(token)
    if not bot:
        return jsonify({"error": "Unauthorized: Invalid token"}), 401
    
    # Xóa dữ liệu tạm thời trong file_store
    file_store.clear()
    
    # Trả về phản hồi xác nhận
    return jsonify({"message": "Data has been reset successfully"}), 200
@app.route('/api/<token>/files', methods=['GET'])
def get_uploaded_files(token):
    # Kiểm tra token có hợp lệ không
    bot = bots.get(token)
    if not bot:
        return jsonify({"error": "Unauthorized: Invalid token"}), 401

    # Tạo danh sách file đã upload cho bot (kèm token của file)
    uploaded_files = []
    for file_token, file_data in file_store.items():
        # Tạo một dictionary với thông tin về file
        uploaded_files.append({
            "file_token": file_token,  # Token của file
            "filename": file_data['filename'],  # Tên file
            "device_token": token  # Token của device gửi file
        })

    if not uploaded_files:
        return jsonify({"message": "No files uploaded yet."}), 200

    return jsonify({
        "device_token": token,
        "uploaded_files": uploaded_files
    }), 200

if __name__ == '__main__':
    # Khởi động thread cập nhật bots

    # Chạy ứng dụng Flask
    app.run(debug=True)
