"""
统一服务器：前端静态文件 + API代理
"""
from flask import Flask, send_from_directory, request, Response
from flask_cors import CORS
import requests
import os

app = Flask(__name__, static_folder='dist')
CORS(app)

API_BACKEND = "http://127.0.0.1:5000"

# API代理 - 放在静态文件路由之前
@app.route('/api/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
def api_proxy(path):
    url = f"{API_BACKEND}/api/{path}"
    # 添加查询参数
    if request.query_string:
        url = f"{url}?{request.query_string.decode()}"
    try:
        if request.method == 'GET':
            resp = requests.get(url, timeout=10)
        elif request.method == 'POST':
            resp = requests.post(url, json=request.get_json(), timeout=10)
        elif request.method == 'OPTIONS':
            return '', 200
        else:
            return {"error": "Method not supported"}, 405
        
        # 添加CORS头
        response = Response(resp.content, status=resp.status_code)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/')
def index():
    return send_from_directory('dist', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('dist', path)

if __name__ == '__main__':
    # 先启动后端API
    import subprocess
    import sys
    sys.path.insert(0, '/root/.openclaw/workspace/quant/quant')
    
    # 启动统一服务器
    app.run(host='0.0.0.0', port=3000)
