import os
import multiprocessing
import time
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import concurrent.futures


def create_app(ai_busy_flag=None):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.abspath(os.path.join(current_dir, '../../../app'))
    template_dir = os.path.join(base_dir, 'web', 'templates')
    static_dir = os.path.join(base_dir, 'web', 'static')

    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    CORS(app)
    app.config['AI_BUSY_FLAG'] = ai_busy_flag

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/api/health')
    def health_check():
        return jsonify({'status': 'ok', 'message': 'Flow State Web Server is running'})

    @app.route('/api/history/scroll')
    def get_history_scroll():
        try:
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            offset = (page - 1) * per_page

            import sqlite3
            from app.data.core.database import get_db_path
            db_path = get_db_path()
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM window_sessions ORDER BY start_time DESC LIMIT ? OFFSET ?",
                (per_page, offset),
            )
            rows = cursor.fetchall()

            records = []
            for s in rows:
                s = dict(s)
                title = s.get('summary') or s.get('window_title') or 'Unknown'
                content_str = f"Status: {s.get('status')} | Duration: {s.get('duration')}s"
                if s.get('process_name'):
                    content_str += f" | App: {s.get('process_name')}"
                records.append({
                    'id': s.get('id'),
                    'timestamp': s.get('start_time'),
                    'app_name': s.get('process_name', 'Unknown'),
                    'window_title': title,
                    'content': content_str,
                    'duration': s.get('duration'),
                    'status': s.get('status')
                })
            conn.close()
            return jsonify({"data": records, "page": page, "has_more": len(records) == per_page})
        except Exception as e:
            return jsonify({"error": str(e), "data": []}), 500

    @app.route('/api/history/check_update')
    def check_update():
        try:
            from app.data.dao.activity_dao import WindowSessionDAO
            last_session = WindowSessionDAO.get_last_session()
            if last_session:
                return jsonify({
                    "latest_id": last_session.get('id'),
                    "latest_timestamp": last_session.get('start_time')
                })
            return jsonify({"latest_id": 0, "latest_timestamp": ""})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/history/recent')
    def get_recent_history():
        try:
            from app.data.dao.activity_dao import WindowSessionDAO
            records = []
            sessions = WindowSessionDAO.get_today_sessions()
            sessions.reverse()
            for s in sessions:
                title = s.get('summary') or s.get('window_title') or 'Unknown'
                content_str = f"Status: {s.get('status')} | Duration: {s.get('duration')}s"
                if s.get('process_name'):
                    content_str += f" | App: {s.get('process_name')}"
                records.append({
                    'id': s.get('id'),
                    'timestamp': s.get('start_time'),
                    'app_name': s.get('process_name', 'Unknown'),
                    'window_title': title,
                    'content': content_str,
                    'duration': s.get('duration'),
                    'status': s.get('status')
                })
            return jsonify(records)
        except Exception:
            return jsonify([])

    @app.route('/api/stats/today')
    def get_today_stats():
        try:
            from app.data.dao.activity_dao import StatsDAO
            from datetime import date
            summary = StatsDAO.get_daily_summary(date.today())
            if not summary:
                return jsonify({
                    "total_focus": 0,
                    "total_work": 0,
                    "total_entertainment": 0,
                    "total_productive_seconds": 0
                })
            focus = summary.get('total_focus_time', 0) or 0
            ent = summary.get('total_entertainment_time', 0) or 0
            return jsonify({
                "total_focus": focus,
                "total_entertainment": ent,
                "total_productive_seconds": focus,
                "max_focus_streak": summary.get('max_focus_streak', 0) or 0,
                "current_focus_streak": summary.get('current_focus_streak', 0) or 0,
                "efficiency_score": summary.get('efficiency_score', 0) or 0
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/report/generate', methods=['POST'])
    def generate_report_api():
        data = request.json or {}
        days = data.get('days', 3)
        flag = app.config.get('AI_BUSY_FLAG')
        if flag:
            flag.value = True
        try:
            from app.data.web_report.report_generator import ReportGenerator
            from app.data.dao.core_events_extractor import extract_core_events
            from app.data.dao.stats_calculator import calculate_period_stats
            from datetime import date, timedelta
            try:
                end_d = date.today()
                start_d = end_d - timedelta(days=days - 1)
                cur = start_d
                while cur <= end_d:
                    d_str = cur.strftime('%Y-%m-%d')
                    extract_core_events(d_str)
                    calculate_period_stats(d_str)
                    cur += timedelta(days=1)
            except Exception:
                pass

            from app.service.ai.langflow_client import LangflowClient
            client = LangflowClient()

            def ai_callback(context):
                core_items = {}
                def process_log(log):
                    date_str = log['date']
                    items_info = log.get('items_context', '')
                    if not items_info and log.get('top_app'):
                         items_info = f"[工作] {log['top_app']} - {log['title']}"
                    if not items_info or len(items_info) <= 5:
                        return None
                    prompt_event = f"""
Role: 你是一个极其敏锐的数据分析师。
Task: 阅读用户在 {date_str} 的主要活动记录，输出当天核心事项的中文短句，使用中文逗号“，”分隔。
Data Context:
{items_info}

Constraints:
- 只输出一行短句，由 2~3 个短语组成，使用“，”分隔。
- 覆盖最重要的 1-2 项工作；如有[娱乐]也要简述，但不要使用括号，直接以短语表达，例如“看B站”。
- 不要使用句号、分号或项目符号；不要加多余说明。
- 总字数 ≤ 30。
- 示例："编写后端代码，调试脚本，看B站"
"""
                    try:
                        res = client.call_flow('summary', prompt_event)
                        return (date_str, res) if res else None
                    except Exception:
                        return None
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    for fut in concurrent.futures.as_completed([executor.submit(process_log, log) for log in context['daily_logs']]):
                        try:
                            r = fut.result()
                            if r:
                                core_items[r[0]] = r[1]
                        except Exception:
                            pass

                peak_info = context['peak_day']
                rows = context.get('period_stats_rows', [])
                top_apps = context.get('top_apps', '')
                total_focus_hours = context['total_focus_hours']
                wins = context['willpower_wins']
                peak_hours = []
                summaries = []
                frag_vals = []
                switch_vals = []
                for r in rows:
                    peak_hours.append(r.get('peak_hour') or 0)
                    s = r.get('daily_summary') or ''
                    if s: summaries.append(s)
                    if r.get('focus_fragmentation_ratio') is not None:
                        frag_vals.append(r.get('focus_fragmentation_ratio'))
                    if r.get('context_switch_freq') is not None:
                        switch_vals.append(r.get('context_switch_freq'))
                days_len = max(1, len(rows))
                from collections import Counter
                best_hour = Counter(peak_hours).most_common(1)[0][0] if peak_hours else 0
                avg_frag = round(sum(frag_vals)/len(frag_vals), 2) if frag_vals else 0
                avg_switch = round(sum(switch_vals)/len(switch_vals), 1) if switch_vals else 0
                summary_join = '；'.join(summaries[:3])
                avg_per_day = round(total_focus_hours / days_len, 1)
                frag_state = '专注占优' if avg_frag >= 1.2 else ('碎片偏多' if avg_frag < 0.8 else '相对平衡')
                switch_state = '切换较频繁' if avg_switch > 18 else ('切换略多' if avg_switch > 12 else '切换控制良好')
                metrics_hint = (
                    f"近{days_len}天平均每天专注约{avg_per_day}小时，克制分心{wins}次。"
                    f"黄金时段多在{best_hour}点，{frag_state}；每小时切换约{avg_switch}次，尽量控制在十几次以内。"
                )
                prompt_enc = f"""
Role: 你是一位深度复盘教练，擅长用事实总结与给出可执行建议。
Task: 写一段“致追梦者”的复盘寄语，要求：
1) 用一句话总结这几天你具体做了什么（结合摘要：{summary_join}；主要阵地：{top_apps}）。
2) 给出数据洞察。不要机械罗列数字，改用口语化描述，如“平均每天约X小时”、“切换较频繁/控制良好”。可参考：{metrics_hint}。
 3) 给出两条可执行建议（例如把“黄金时段”用于高强任务、降低切换频率、提升碎片比）。两条建议必须换行，行首标注“建议1：”“建议2：”。
 4) 风格简洁真诚，不夸张，不口号；中文 3-4 句，合计不超过 160 字。
"""
                encouragement = client.call_flow('enc', prompt_enc) or "AI 暂时繁忙，但数据见证了你的努力。继续加油！"
                return {"core_items": core_items, "encouragement": encouragement}

            from app.data.web_report.report_generator import ReportGenerator
            generator = ReportGenerator()
            report_md = generator.generate_report(days=days, ai_callback=ai_callback)
            return jsonify({"report": report_md})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500
        finally:
            if flag:
                flag.value = False

    @app.route('/api/generate_report_old', methods=['POST'])
    def generate_report_old():
        flag = app.config.get('AI_BUSY_FLAG')
        if flag:
            flag.value = True
        try:
            time.sleep(3)
            return jsonify({"report": "今日专注效率很高，专注时长2小时..."})
        finally:
            if flag:
                flag.value = False

    @app.route('/api/chat', methods=['POST'])
    def chat_with_ai():
        data = request.json or {}
        user_msg = data.get('message', '')
        if not user_msg:
            return jsonify({"error": "Empty message"}), 400
        flag = app.config.get('AI_BUSY_FLAG')
        if flag:
            flag.value = True
        try:
            from app.data.dao.activity_dao import ActivityDAO
            from app.service.detector.detector_logic import analyze
            recent_activities = ActivityDAO.get_recent_activities(limit=20)
            lines = []
            for act in recent_activities or []:
                title = act.get('summary') or "未知窗口"
                if 'raw_data' in act and act['raw_data']:
                    try:
                        import json
                        rd = json.loads(act['raw_data'])
                        title = rd.get('window', title)
                    except Exception:
                        pass
                ts = act.get('timestamp')
                lines.append(f"- [{ts}] {title} (状态: {act.get('status')})")
            context_str = "\n".join(lines)
            system_prompt = f"""
你是一个 Flow State 效率助手。用户正在询问关于他的工作/学习情况。
以下是用户最近的活动记录（作为参考）：
{context_str}

请根据上述记录回答用户的问题。如果记录中没有相关信息，请诚实回答。
保持回答简练、友好、有建设性。不要使用 JSON 格式回复，直接输出 Markdown 文本。
"""
            response_text = analyze(user_msg, system_prompt=system_prompt, json_mode=False)
            return jsonify({"response": response_text})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            if flag:
                flag.value = False

    @app.route('/api/settings/autostart', methods=['GET', 'POST'])
    def autostart_setting():
        try:
            import win32com.client
            import pythoncom
            import sys
            startup_folder = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup')
            shortcut_path = os.path.join(startup_folder, 'FlowState.lnk')
            if request.method == 'GET':
                return jsonify({"enabled": os.path.exists(shortcut_path)})
            data = request.json or {}
            enable = data.get('enabled', False)
            if enable:
                pythoncom.CoInitialize()
                root_dir = os.path.abspath(os.path.join(current_dir, '../../../'))
                target_script = os.path.join(root_dir, 'run.py')
                if not os.path.exists(target_script):
                    pythoncom.CoUninitialize()
                    return jsonify({"error": "Cannot find run.py"}), 500
                python_exe = sys.executable
                pythonw_exe = python_exe.replace('python.exe', 'pythonw.exe')
                target_exe = pythonw_exe if os.path.exists(pythonw_exe) else python_exe
                shell = win32com.client.Dispatch("WScript.Shell")
                shortcut = shell.CreateShortCut(shortcut_path)
                shortcut.TargetPath = target_exe
                shortcut.Arguments = f'"{target_script}"'
                shortcut.WorkingDirectory = root_dir
                shortcut.Description = "Flow State Auto Start"
                shortcut.IconLocation = python_exe
                shortcut.save()
                pythoncom.CoUninitialize()
                return jsonify({"enabled": True, "message": "Autostart enabled"})
            else:
                if os.path.exists(shortcut_path):
                    os.remove(shortcut_path)
                return jsonify({"enabled": False, "message": "Autostart disabled"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/sessions/manual/add', methods=['POST'])
    def add_manual_session():
        try:
            data = request.json
            start_time = data.get('start_time')
            end_time = data.get('end_time')
            summary = data.get('summary')
            status = data.get('status') # focus/entertainment

            if not all([start_time, end_time, summary, status]):
                return jsonify({"error": "Missing fields"}), 400

            from app.data.dao.activity_dao import WindowSessionDAO, StatsDAO
            
            # Check overlap
            if WindowSessionDAO.check_overlap(start_time, end_time):
                return jsonify({"error": "Time range overlaps with existing sessions"}), 409

            # Create
            WindowSessionDAO.create_manual_session(start_time, end_time, summary, status)
            
            # Recompute stats
            StatsDAO.recompute_today_from_sessions()
            
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/sessions/manual/delete', methods=['POST'])
    def delete_manual_session():
        try:
            data = request.json
            session_id = data.get('id')
            if not session_id:
                return jsonify({"error": "Missing ID"}), 400

            from app.data.dao.activity_dao import WindowSessionDAO, StatsDAO
            
            WindowSessionDAO.delete_session(session_id)
            StatsDAO.recompute_today_from_sessions()
            
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/sessions/manual/list', methods=['GET'])
    def list_manual_sessions():
        try:
            from app.data.dao.activity_dao import WindowSessionDAO
            limit = request.args.get('limit', 50, type=int)
            sessions = WindowSessionDAO.get_manual_sessions(limit)
            return jsonify(sessions)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app


def run_server(port=5000, ai_busy_flag=None):
    print(f"【Web服务进程】启动 (PID: {multiprocessing.current_process().pid}) http://127.0.0.1:{port}")
    app = create_app(ai_busy_flag)
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


if __name__ == '__main__':
    run_server()
