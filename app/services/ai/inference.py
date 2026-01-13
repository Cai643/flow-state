"""
专注力提升APP - 主程序
完整的API服务器，无依赖问题
"""

from flask import Flask, request, jsonify, g
from flask_cors import CORS
from functools import wraps
import jwt
import hashlib
from datetime import datetime, timedelta
import json
import os
import time
from dataclasses import dataclass
from typing import Dict, Optional

# 使用新的 DAO (统一从 app.data 导入)
from app.data import UserDAO

app = Flask(__name__)
CORS(app)

# ==================== 配置 ====================

class Config:
    """API配置"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
    # DATABASE_PATH 由 app.data.base 统一管理
    TOKEN_EXPIRATION_HOURS = 24
    API_VERSION = 'v1'
    HOST = '0.0.0.0'
    PORT = 5000
    DEBUG = True
    
app.config.from_object(Config)


# ==================== 数据模型 (保持不变) ====================
# ... (Dataclasses for MouseData, KeyboardData, etc. omitted for brevity as they are unchanged)

# ==================== 运行时状态 ====================

_runtime_state = {
    'current_status': None,
    'status_started_at': None,
    'durations': {}
}


# ==================== 分析逻辑 ====================

def _classify_status(monitor_data: Dict) -> str:
    """根据画面变化率判断状态"""
    change = float(monitor_data.get('screen_change_rate', 0.0) or 0.0)
    
    if change > 0.05:
        status = 'entertainment'
    elif change > 0.02:
        status = 'work'
    else:
        status = 'focus'
    
    print(f"[API] 画面变化率: {change:.4f} -> 判定状态: {status}")
    return status

def _status_message(status: str) -> str:
    return {
        'entertainment': '检测到大幅动作或高动态画面，可能在休息或娱乐。',
        'work': '检测到正常活动，正在工作中。',
        'focus': '画面基本静止，深度专注中。',
    }.get(status, '状态未知。')

def get_analysis(monitor_data: Dict) -> Dict:
    """供项目调用的轻量分析函数"""
    now = time.time()
    status = _classify_status(monitor_data)

    if _runtime_state['current_status'] != status:
        _runtime_state['current_status'] = status
        _runtime_state['status_started_at'] = now

    started = _runtime_state['status_started_at'] or now
    duration = now - started
    _runtime_state['durations'][status] = duration

    return {
        'status': status,
        'duration': int(duration),
        'message': _status_message(status)
    }


# ==================== 认证中间件 ====================

def token_required(f):
    """Token验证装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'success': False, 'error': 'Token格式错误'}), 401
        
        if not token: 
            return jsonify({'success': False, 'error': '缺少认证Token'}), 401
        
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_username = data['username']
            
            # 使用 DAO 验证用户
            user = UserDAO.get_user_by_username(current_username)
            
            if not user:
                return jsonify({'success': False, 'error': '用户不存在'}), 401
            
            g.current_user = user
            
        except jwt.ExpiredSignatureError:
            return jsonify({'success': False, 'error': 'Token已过期'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'error':  '无效的Token'}), 401
        
        return f(*args, **kwargs)
    
    return decorated


# ==================== API路由 ====================

@app.route(f'/api/{Config.API_VERSION}/auth/register', methods=['POST'])
def register():
    """用户注册"""
    try: 
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        email = data.get('email', '')
        
        if not username or not password:
            return jsonify({'success': False, 'error': '用户名和密码不能为空'}), 400
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # 使用 DAO 创建用户
        success, message = UserDAO.create_user(username, password_hash, email)
        
        if success:
            return jsonify({'success': True, 'message': message}), 201
        else:
            return jsonify({'success': False, 'error': message}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route(f'/api/{Config.API_VERSION}/auth/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'success': False, 'error': '用户名和密码不能为空'}), 400
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # 使用 DAO 验证登录
        user = UserDAO.get_user_by_username(username)
        
        if not user or user['password_hash'] != password_hash:
            return jsonify({'success': False, 'error': '用户名或密码错误'}), 401
        
        token = jwt.encode({
            'user_id': user['id'],
            'username': user['username'],
            'exp': datetime.utcnow() + timedelta(hours=Config.TOKEN_EXPIRATION_HOURS)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            'success': True,
            'token': token,
            'user':  {
                'id': user['id'],
                'username': user['username']
            }
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route(f'/api/{Config.API_VERSION}/page/recognize', methods=['POST'])
@token_required
def recognize_current_page():
    return jsonify({'success': True, 'message': 'Not implemented yet'}), 200

@app.route(f'/api/{Config.API_VERSION}/video/learning-quality', methods=['POST'])
@token_required
def analyze_video_learning_quality():
    return jsonify({'success': True, 'message': 'Not implemented yet'}), 200

if __name__ == '__main__':
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
