# -*- coding: gbk -*-
import os
import multiprocessing
import time
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

def create_app(ai_busy_flag=None):
    # Get app directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    
    if not os.path.basename(app_dir) == 'app':
        pass

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
    
    # Window Sessions
    @app.route('/api/history/scroll')
    def get_history_scroll():
        try:
            from app.data.dao.activity_dao import WindowSessionDAO
            
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            
            offset = (page - 1) * per_page
            
            import sqlite3
            from app.data.core.database import get_db_path
            
            db_path = get_db_path()
            print(f"[WebAPI] Connecting to DB at: {db_path}") 
            
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = """
                SELECT * FROM window_sessions 
                ORDER BY start_time DESC 
                LIMIT ? OFFSET ?
            """
            cursor.execute(query, (per_page, offset))
            rows = cursor.fetchall()
            
            records = []
            for s in rows:
                s = dict(s)
                
                title = s.get('summary')
                if not title or title == s.get('window_title'):
                    title = s.get('window_title', 'Unknown')
                    
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
            
            return jsonify({
                "data": records,
                "page": page,
                "has_more": len(records) == per_page
            })
            
        except Exception as e:
            print(f"Error fetching scroll history: {e}")
            return jsonify({"error": str(e), "data": []}), 500

    @app.route('/api/history/check_update')
    def check_update():
        """Check for updates"""
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
            print(f"Error checking update: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/history/recent')
    def get_recent_history():
        try:
            from app.data.dao.activity_dao import WindowSessionDAO
            import json
            
            records = []
            
            sessions = WindowSessionDAO.get_today_sessions()
            sessions.reverse()
            
            if sessions:
                for s in sessions:
                    title = s.get('summary')
                    if not title or title == s.get('window_title'):
                        title = s.get('window_title', 'Unknown')
                        
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
            
            if not records:
                pass 

            return jsonify(records)
        except Exception as e:
            print(f"Error fetching history: {e}")
            return jsonify([])

    @app.route('/api/stats/today')
    def get_today_stats():
        try:
            from app.data.dao.activity_dao import StatsDAO
            from datetime import date
            
            today = date.today()
            summary = StatsDAO.get_daily_summary(today)
            
            if not summary:
                return jsonify({
                    "total_focus": 0,
                    "total_work": 0,
                    "total_entertainment": 0,
                    "total_productive_seconds": 0
                })
                
            focus = summary.get('total_focus_time', 0) or 0
            ent = summary.get('total_entertainment_time', 0) or 0
            
            max_streak = summary.get('max_focus_streak', 0) or 0
            current_streak = summary.get('current_focus_streak', 0) or 0
            efficiency = summary.get('efficiency_score', 0) or 0
            
            return jsonify({
                "total_focus": focus,
                "total_entertainment": ent,
                "total_productive_seconds": focus, 
                "max_focus_streak": max_streak,
                "current_focus_streak": current_streak,
                "efficiency_score": efficiency
            })
        except Exception as e:
            print(f"Error fetching stats: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/report/generate', methods=['POST'])
    def generate_report_api():
        data = request.json
        days = data.get('days', 3)
        print(f"[Web Service] Generate report request, days: {days}")
        
        flag = app.config.get('AI_BUSY_FLAG')
        if flag:
            flag.value = True
            
        try:
            from app.data.web_report.report_generator import ReportGenerator
            from app.service.detector.extract_core_events import extract_core_events
            from app.service.detector.calculate_period_stats import calculate_period_stats
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
            except Exception as e:
                print(f"[Web Service] Extract failed: {e}")

            from app.service.ai.langflow_client import LangflowClient
            client = LangflowClient()
            import concurrent.futures

            def ai_callback(context):
                print("[Web Service] Requesting AI (LangFlow)...")
                
                core_items = {}
                
                def process_log(log):
                    date_str = log['date']
                    
                    items_info = log.get('items_context', '')
                    if not items_info and log.get('top_app'):
                         items_info = f"[Work] {log['top_app']} - {log['title']}"

                    if not items_info or len(items_info) <= 5:
                        print(f"  [AI] Skip {date_str} (not enough info)")
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
                    print(f"  [AI] Generating summary for {date_str}...")
                    try:
                        res = client.call_flow('summary', prompt_event)
                        if res: 
                            print(f"  [AI] Result for {date_str}: {res}")
                            return (date_str, res)
                        else:
                            print(f"  [AI] Failed to get response for {date_str}")
                            return None
                    except Exception as e:
                        print(f"  [AI] Error processing {date_str}: {e}")
                        return None

                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    futures = [executor.submit(process_log, log) for log in context['daily_logs']]
                    for future in concurrent.futures.as_completed(futures):
                        try:
                            result = future.result()
                            if result:
                                core_items[result[0]] = result[1]
                        except Exception as e:
                            print(f"  [AI] Thread error: {e}")
                
                peak_info = context['peak_day']
                peak_str = f"{peak_info.get('date_str', 'None')} ({peak_info.get('hours', 0)}h)"
                rows = context.get('period_stats_rows', [])
                top_apps = context.get('top_apps', '')
                
                total_focus_hours = context['total_focus_hours']
                wins = context['willpower_wins']
                avg_eff = 0
                peak_hours = []
                summaries = []
                frag_vals = []
                switch_vals = []
                for r in rows:
                    avg_eff += (r.get('efficiency_score') or 0)
                    peak_hours.append(r.get('peak_hour') or 0)
                    s = r.get('daily_summary') or ''
                    if s: summaries.append(s)
                    if r.get('focus_fragmentation_ratio') is not None:
                        frag_vals.append(r.get('focus_fragmentation_ratio'))
                    if r.get('context_switch_freq') is not None:
                        switch_vals.append(r.get('context_switch_freq'))
                days_len = max(1, len(rows))
                avg_eff = int(avg_eff / days_len)
                
                from collections import Counter
                best_hour = 0
                if peak_hours:
                    best_hour = Counter(peak_hours).most_common(1)[0][0]
                avg_frag = round(sum(frag_vals)/len(frag_vals), 2) if frag_vals else 0
                avg_switch = round(sum(switch_vals)/len(switch_vals), 1) if switch_vals else 0
                summary_join = '；'.join(summaries[:3])  

                avg_per_day = round(total_focus_hours / days_len, 1)
                frag_state = (
                    '专注占优' if avg_frag >= 1.2 else (
                        '碎片偏多' if avg_frag < 0.8 else '相对平衡'
                    )
                )
                switch_state = (
                    '切换较频繁' if avg_switch > 18 else (
                        '切换略多' if avg_switch > 12 else '切换控制良好'
                    )
                )
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
                encouragement = client.call_flow('enc', prompt_enc)
                if not encouragement:
                    encouragement = "AI is busy. Keep going!"

                return {
                    "core_items": core_items,
                    "encouragement": encouragement
                }

            generator = ReportGenerator()
            report_md = generator.generate_report(days=days, ai_callback=ai_callback)
            
            return jsonify({"report": report_md})
            
        except Exception as e:
            print(f"[Web Service] Report failed: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500
        finally:
            if flag:
                flag.value = False

    @app.route('/api/generate_report_old', methods=['POST'])
    def generate_report_old():
        print("[Web Service] Old report request...")
        
        flag = app.config.get('AI_BUSY_FLAG')
        if flag:
            flag.value = True
            
        try:
            time.sleep(3) 
            return jsonify({"report": "Done."})
        finally:
            if flag:
                flag.value = False

    @app.route('/api/chat', methods=['POST'])
    def chat_with_ai():
        data = request.json
        user_msg = data.get('message', '')
        if not user_msg:
            return jsonify({"error": "Empty message"}), 400

        print(f"[Web Service] Chat request: {user_msg}")
        
        flag = app.config.get('AI_BUSY_FLAG')
        if flag:
            flag.value = True
            
        try:
            from app.data.dao.activity_dao import ActivityDAO
            from app.service.detector.detector_logic import analyze
            
            recent_activities = ActivityDAO.get_recent_activities(limit=20)
            context_str = ""
            if recent_activities:
                lines = []
                for act in recent_activities:
                    title = act.get('summary') or "Unknown Window"
                    if 'raw_data' in act and act['raw_data']:
                        try:
                            import json
                            rd = json.loads(act['raw_data'])
                            title = rd.get('window', title)
                        except: pass
                    
                    ts = act.get('timestamp')
                    lines.append(f"- [{ts}] {title} (Status: {act.get('status')})")
                context_str = "\n".join(lines)
            
            system_prompt = f"""
            你是一个 Flow State 效率助手。用户正在询问关于他的工作/学习情况。
            以下是用户最近的活动记录（作为参考）：
            {context_str}
            
            请根据上述记录回答用户的问题。如果记录中没有相关信息，请诚实回答。
            保持回答简练、友好、有建设性。不要使用 JSON 格式回复，直接输出 Markdown 文本。
            """
            
            response_text = analyze(user_msg, system_prompt=system_prompt, json_mode=False)
            
            final_resp = response_text

            return jsonify({"response": final_resp})
            
        except Exception as e:
            print(f"[Web Service] Chat failed: {e}")
            return jsonify({"error": str(e)}), 500
        finally:
            if flag:
                flag.value = False

    # Autostart API
    @app.route('/api/settings/autostart', methods=['GET', 'POST'])
    def autostart_setting():
        try:
            import win32com.client
            import sys
            
            startup_folder = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup')
            shortcut_path = os.path.join(startup_folder, 'FlowState.lnk')
            
            if request.method == 'GET':
                is_enabled = os.path.exists(shortcut_path)
                return jsonify({"enabled": is_enabled})
            
            elif request.method == 'POST':
                data = request.json
                enable = data.get('enabled', False)
                
                if enable:
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    root_dir = os.path.abspath(os.path.join(current_dir, '../../../'))
                    target_script = os.path.join(root_dir, 'run.py')
                    
                    if not os.path.exists(target_script):
                        return jsonify({"error": "Cannot find run.py"}), 500
                        
                    python_exe = sys.executable
                    pythonw_exe = python_exe.replace('python.exe', 'pythonw.exe')
                    if os.path.exists(pythonw_exe):
                        target_exe = pythonw_exe
                    else:
                        target_exe = python_exe
                        
                    shell = win32com.client.Dispatch("WScript.Shell")
                    shortcut = shell.CreateShortCut(shortcut_path)
                    shortcut.TargetPath = target_exe
                    shortcut.Arguments = f'"{target_script}"'
                    shortcut.WorkingDirectory = root_dir
                    shortcut.Description = "Flow State Auto Start"
                    shortcut.IconLocation = python_exe
                    shortcut.save()
                    
                    return jsonify({"enabled": True, "message": "Autostart enabled"})
                    
                else:
                    if os.path.exists(shortcut_path):
                        os.remove(shortcut_path)
                    return jsonify({"enabled": False, "message": "Autostart disabled"})
                    
        except Exception as e:
            print(f"Error managing autostart: {e}")
            return jsonify({"error": str(e)}), 500

    return app

def run_server(port=5000, ai_busy_flag=None):
    """
    Start Web Server
    """
    print(f"[Web Service Process] Start (PID: {multiprocessing.current_process().pid}) http://127.0.0.1:{port}")
    try:
        app = create_app(ai_busy_flag)
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        print(f"[Web Service Process] Start failed: {e}")

if __name__ == '__main__':
    run_server()
