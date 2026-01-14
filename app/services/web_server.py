import os
import multiprocessing
from flask import Flask, render_template, jsonify, request, send_from_directory, make_response
from flask_cors import CORS
import time

def create_app():
    # Get absolute paths for templates and static
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(base_dir, 'web', 'templates')
    static_dir = os.path.join(base_dir, 'web', 'static')

    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    CORS(app) 

    @app.route('/')
    def index():
        # Robust file reading: Try UTF-8 first, fallback to GBK/GB18030 for Windows compatibility
        path = os.path.join(template_dir, 'index.html')
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(path, 'r', encoding='gb18030') as f:
                    content = f.read()
            except Exception as e:
                return f"Error loading template (encoding failure): {str(e)}", 500
        except Exception as e:
            return f"Error loading template: {str(e)}", 500
            
        return content

    @app.route('/api/health')
    def health_check():
        return jsonify({'status': 'ok', 'message': 'Flow State Web Server is running'})
    
    # API: Get History
    @app.route('/api/history')
    def get_history():
        # TODO: Call app.data.dao to read SQLite
        return jsonify({"date": "2026-01-13", "focus_time": 120})

    @app.route('/api/history/recent')
    def get_recent_history():
        days = request.args.get('days', default=7, type=int)
        try:
            from app.data.dao.activity_dao import OcrDAO
            # TODO: Pass days to DAO to filter by date
            records = OcrDAO.get_recent_records(limit=50)
            
            # Mock data generation if DB is empty
            if not records:
                import datetime
                import random
                base_time = datetime.datetime.now()
                records = []
                apps = ['Chrome', 'VS Code', 'WeChat', 'Word', 'Edge']
                titles = ['Flow State Project - Design', 'app.py - flow-state', 'Team Chat', 'Requirements.docx', 'Stack Overflow - Python Flask']
                
                # Generate more data if requesting 30 days
                count = 50 if days > 7 else 15
                
                for i in range(count):
                    # Spread mock data over the requested period
                    delta_days = random.randint(0, days - 1)
                    delta_mins = random.randint(0, 1440)
                    timestamp = base_time - datetime.timedelta(days=delta_days, minutes=delta_mins)
                    
                    records.append({
                        'id': i,
                        'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        'app_name': apps[i % len(apps)],
                        'window_title': titles[i % len(titles)],
                        'content': 'Simulated content for demo purposes...'
                    })
                
                # Sort by timestamp desc
                records.sort(key=lambda x: x['timestamp'], reverse=True)
                
            return jsonify(records)
        except Exception as e:
            print(f"Error fetching history: {e}")
            return jsonify([])

    # API: AI Generate Report
    @app.route('/api/generate_report', methods=['POST'])
    def generate_report():
        print("[Web] Calling AI model for report...")
        time.sleep(3) # Simulate AI thinking
        return jsonify({"report": "You focused for 2 hours today..."})

    return app

def run_server(port=5000):
    """
    Run Web Server
    Note: When running in PyQt thread, set use_reloader=False
    """
    print(f"[Web Process] Started (PID: {multiprocessing.current_process().pid}) http://127.0.0.1:{port}")
    app = create_app()
    # use_reloader=False is crucial when running inside a thread/process from another app
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == '__main__':
    run_server()
