"""
统一服务器：前端静态文件 + API代理
"""
from flask import Flask, send_from_directory, proxy
import requests

app = Flask(__name__, static_folder='dist')

# API后端地址
API_BACKEND = "http://127.0.0.1:5000"

@app.route('/')
def index():
    return send_from_directory('dist', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('dist', path)

# 代理API请求
@app.route('/api/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_proxy(path):
    url = f"{API_BACKEND}/api/{path}"
    try:
        if requests.method == 'GET':
            resp = requests.get(url, timeout=10)
        elif requests.method == 'POST':
            resp = requests.post(url, json=requests.json, timeout=10)
        else:
            return {"error": "Method not supported"}, 405
        return resp.content, resp.status_code
    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
