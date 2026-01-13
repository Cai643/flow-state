import os
import multiprocessing
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import time

def create_app():
    # 获取 app/web/templates 和 app/web/static 的绝对路径
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(base_dir, 'web', 'templates')
    static_dir = os.path.join(base_dir, 'web', 'static')

    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    CORS(app) # 允许跨域，方便前端开发

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/api/health')
    def health_check():
        return jsonify({'status': 'ok', 'message': 'Flow State Web Server is running'})
    
    # 示例：获取历史数据接口
    @app.route('/api/history')
    def get_history():
        # TODO: 实际应调用 app.data.dao 读取 SQLite
        # from app.data.dao.activity_dao import ActivityDAO
        return jsonify({"date": "2026-01-13", "focus_time": 120})

    # 示例：AI 生成日报接口
    @app.route('/api/generate_report', methods=['POST'])
    def generate_report():
        print("【Web】正在调用大模型生成日报...")
        time.sleep(3) # 模拟 AI 思考
        return jsonify({"report": "你今天效率很高，专注了2小时..."})

    return app

def run_server(port=5000):
    """
    运行 Web 服务器
    注意：在 PyQt 线程中调用时，需要设置 use_reloader=False 避免二次启动
    """
    print(f"【Web服务进程】启动 (PID: {multiprocessing.current_process().pid}) http://127.0.0.1:{port}")
    app = create_app()
    # use_reloader=False is crucial when running inside a thread/process from another app
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == '__main__':
    run_server()