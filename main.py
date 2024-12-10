import secrets
from flask import Flask, request, jsonify, send_file
import requests

app = Flask(__name__)

# Hàm tạo token ngẫu nhiên (20 ký tự)
def generate_token(length=20):
    return ''.join(secrets.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(length))

# Danh sách bot lưu trữ tạm thời
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

# Lưu trữ token (có thể là database hoặc trong bộ nhớ tạm thời)
file_store = {}

@app.route('/api/<token>/upload', methods=['POST'])
def upload_file(token):
    # Kiểm tra token
    bot = bots.get(token)
    if not bot:
        return jsonify({"error": "Unauthorized: Invalid token"}), 401

    # Kiểm tra xem file có tồn tại không
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No file selected for uploading"}), 400

    # Lấy token từ form data
    token_data = request.form.get('token')

    # Lưu dữ liệu file vào `file_store`, phân loại theo token
    if token not in file_store:
        file_store[token] = []

    file_store[token].append({
        "file_token": token_data,
        "filename": file.filename,
        "content": file.read()
    })

    return jsonify({
        "message": f"File uploaded successfully by {bot['name']}",
        "download_token": token_data
    }), 200

@app.route('/api/<token>/files', methods=['GET'])
def get_uploaded_files(token):
    # Kiểm tra token có hợp lệ không
    bot = bots.get(token)
    if not bot:
        return jsonify({"error": "Unauthorized: Invalid token"}), 401

    # Lấy danh sách file được lưu bởi token
    uploaded_files = file_store.get(token, [])

    if not uploaded_files:
        return jsonify({"message": "No files uploaded yet."}), 200

    # Trả về danh sách file
    return jsonify({
        "device_token": token,
        "uploaded_files": [
            {
                "file_token": file["file_token"],
                "filename": file["filename"]
            }
            for file in uploaded_files
        ]
    }), 200

# @app.route('/download/<token>', methods=['GET'])
# def download_file(token):
#     # Kiểm tra token tồn tại
#     file_data = file_store.get(token)
#     if not file_data:
#         return jsonify({"error": "Invalid or expired token"}), 404

#     # Trả file về client
#     file_bytes = io.BytesIO(file_data['content'])
#     file_bytes.seek(0)
#     # file_store.clear()
#     return send_file(
#         file_bytes,
#         mimetype='application/octet-stream',
#         as_attachment=True,
#         download_name=file_data['filename']
#     )
stored_devices = {}

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
        required_fields = ['token', 'name_device', 'IP', 'City', 'Area', 'Country', 'Location', 'Network_provider']
        if not all(field in device for field in required_fields):
            failed_devices.append({"error": "Invalid device format.", "device": device})
            continue

        token = device['token']

        # Kiểm tra nếu token đã tồn tại
        if token in stored_devices:
            failed_devices.append({"error": "Device with this token already exists.", "device": device})
            continue

        # Thêm thiết bị vào danh sách
        stored_devices[token] = {
            "name_device": device['name_device'],
            "IP": device['IP'],
            "City": device['City'],
            "Area": device['Area'],
            "Country": device['Country'],
            "Location": device['Location'],
            "Network_provider": device['Network_provider']
        }
        added_devices.append({"token": token, "name_device": device['name_device']})

    return jsonify({
        "message": "Devices processed.",
        "added_devices": added_devices,
        "failed_devices": failed_devices
    }), 200

@app.route('/api/newdevice/list', methods=['GET'])
def list_devices():
    # Trả về danh sách tất cả các thiết bị
    devices = []
    for token, info in stored_devices.items():
        device = {"token": token}
        device.update(info)
        devices.append(device)
    return jsonify({"devices": devices}), 200

@app.route('/api/<token>/reset_data', methods=['GET'])
def reset_data(token):
    bot = bots.get(token)
    if not bot:
        return jsonify({"error": "Unauthorized: Invalid token"}), 401
    
    # Xóa dữ liệu tạm thời trong file_store
    file_store.clear()
    
    # Trả về phản hồi xác nhận
    return jsonify({"message": "Data has been reset successfully"}), 200


if __name__ == '__main__':
    # Khởi động thread cập nhật bots

    # Chạy ứng dụng Flask
    app.run(debug=True)
