import os
import multiprocessing
from flask import Flask, jsonify, request
from flask_cors import CORS

from app.data.dao.activity_dao import (
    insert_activity_log, init_activity_logs_db, fetch_latest_activity
)
from app.data.services.activity_service import summarize_activity

def create_app():
    app = Flask(__name__)
    CORS(app)
    init_activity_logs_db()

    @app.route("/")
    def index():
        return "<h1>Flow State Server Ok</h1>"

    @app.route("/api/status/current")
    def get_current_status():
        latest = fetch_latest_activity()
        if latest:
            return jsonify({
                "code": 200,
                "data": latest
            })
        else:
            return jsonify({"code": 404, "msg": "No data"})

    @app.route("/api/activity/record", methods=["POST"])
    def post_activity_log():
        """
        POST JSON:
        {
            "status": "focus"|"entertainment"|"idle"|"distracted",
            "timestamp": 1705046400.0,
            "duration": 120
        }
        """
        data = request.get_json(force=True)
        status = data.get("status")
        timestamp = data.get("timestamp")
        duration = data.get("duration")
        if status not in {"focus", "entertainment", "idle", "distracted"}:
            return jsonify({"code":400, "msg":"invalid status"}), 400
        if timestamp is None or duration is None:
            return jsonify({"code":400, "msg":"missing params"}), 400
        try:
            insert_activity_log(status, float(timestamp), int(duration))
            return jsonify({"code":200, "msg":"success"})
        except Exception as e:
            return jsonify({"code":500, "msg":str(e)}), 500

    @app.route("/api/history")
    def get_history():
        """
        GET /api/history?date=2026-01-14
        """
        date = request.args.get("date")
        if not date:
            return jsonify({"code":400, "msg":"missing date"}), 400
        try:
            summary = summarize_activity(date)
            return jsonify({"code":200, "data":summary})
        except Exception as e:
            return jsonify({"code":500, "msg":str(e)}), 500

    return app

def run_server(port=5000):
    print(f"[Web Server Process] Started (PID: {multiprocessing.current_process().pid}) http://127.0.0.1:{port}")
    app = create_app()
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == '__main__':
    run_server()