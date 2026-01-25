import os
import multiprocessing
import time
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

def create_app(ai_busy_flag=None):
    # 获取 app 目录 (假设当前文件在 app/service/API/web_API.py)
    # 1. .../app/service/API
    # 2. .../app/service
    # 3. .../app
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    
    # 如果上面计算不对，可以使用绝对路径查找
    # 也可以直接定位到 c:\心境项目\flow_state\app
    if not os.path.basename(app_dir) == 'app':
        # Fallback or explicit check
        # 尝试向上查找直到找到 app 目录
        pass

    # 简便起见，我们知道结构是 app/web/templates
    # 从 app/service/API/web_API.py 到 app/web/templates
    # ../../../web/templates
    
    base_dir = os.path.abspath(os.path.join(current_dir, '../../../app'))
    template_dir = os.path.join(base_dir, 'web', 'templates')
    static_dir = os.path.join(base_dir, 'web', 'static')

    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    CORS(app) # 允许跨域，方便前端开发

    # 挂载 flag 到 app 配置中，方便路由访问
    app.config['AI_BUSY_FLAG'] = ai_busy_flag

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/api/health')
    def health_check():
        return jsonify({'status': 'ok', 'message': 'Flow State Web Server is running'})
    
    # 分页获取历史会话数据接口 (Window Sessions)
    @app.route('/api/history/scroll')
    def get_history_scroll():
        try:
            from app.data.dao.activity_dao import WindowSessionDAO
            
            # 获取分页参数
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            
            # 计算偏移量
            offset = (page - 1) * per_page
            
            # 临时直接调用底层逻辑 (为了快速实现)
            import sqlite3
            from app.data.core.database import get_db_path
            
            db_path = get_db_path()
            print(f"[WebAPI] Connecting to DB at: {db_path}") # Debug log
            
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 使用 window_sessions 表，按开始时间倒序排列
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
                
                # 优先使用 summary (AI 摘要)，如果没有则使用窗口标题
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
        """检查是否有新数据"""
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
            # 延迟导入以避免循环依赖或上下文问题
            from app.data.dao.activity_dao import WindowSessionDAO
            import json
            
            records = []
            
            # 1. 优先使用 Window Sessions (聚合后的高质量数据)
            # 获取今天的会话 (或者可以修改 DAO 支持获取最近 N 条)
            sessions = WindowSessionDAO.get_today_sessions()
            
            # 如果今天还没数据，或者太少，可以尝试获取最近的 N 条 (需修改 DAO，暂用 today)
            # 反转顺序，让最新的在前面
            sessions.reverse()
            
            if sessions:
                for s in sessions:
                    # s: id, start_time, end_time, window_title, duration, status, summary
                    
                    # 优先使用 summary (AI 摘要)，如果没有则使用窗口标题
                    title = s.get('summary')
                    if not title or title == s.get('window_title'):
                        # 如果 summary 和 window_title 一样，可能是还没被 AI 润色
                        # 尝试从 window_title 截取更有意义的部分
                        title = s.get('window_title', 'Unknown')
                        
                    content_str = f"Status: {s.get('status')} | Duration: {s.get('duration')}s"
                    if s.get('process_name'):
                        content_str += f" | App: {s.get('process_name')}"

                    records.append({
                        'id': s.get('id'),
                        'timestamp': s.get('start_time'), # 已经是字符串格式
                        'app_name': s.get('process_name', 'Unknown'),
                        'window_title': title, # 这里放摘要或标题
                        'content': content_str,
                        'duration': s.get('duration'),
                        'status': s.get('status')
                    })
            
            # 2. 如果 Window Sessions 没数据 (比如刚启动)，尝试获取 OCR 记录
            # if not records:
            #     ocr_records = OcrDAO.get_recent_records(limit=50)
            #     if ocr_records:
            #         # OCR records might need similar timestamp handling if they are datetime objects
            #         for ocr in ocr_records:
            #             ts = ocr.get('timestamp')
            #             if hasattr(ts, 'strftime'):
            #                 ts_str = ts.strftime('%Y-%m-%d %H:%M:%S')
            #             else:
            #                 ts_str = str(ts) if ts else ''
            #                 
            #             records.append({
            #                 'id': ocr.get('id'),
            #                 'timestamp': ts_str,
            #                 'app_name': ocr.get('app_name'),
            #                 'window_title': ocr.get('window_title'),
            #                 'content': ocr.get('content')
            #             })

            # 3. 如果都没有数据，生成一些模拟数据供演示
            if not records:
                # 即使没有数据，也不要返回模拟数据，返回空列表，前端会显示"暂无记录"
                pass 

            return jsonify(records)
        except Exception as e:
            print(f"Error fetching history: {e}")
            return jsonify([])

    # 新增：获取今日专注统计
    @app.route('/api/stats/today')
    def get_today_stats():
        try:
            from app.data.dao.activity_dao import StatsDAO
            from datetime import date
            
            today = date.today()
            summary = StatsDAO.get_daily_summary(today)
            
            # 如果还没有数据，返回 0
            if not summary:
                return jsonify({
                    "total_focus": 0,
                    "total_work": 0,
                    "total_entertainment": 0,
                    "total_productive_seconds": 0
                })
                
            # 计算总有效时长 (focus + work)
            focus = summary.get('total_focus_time', 0) or 0
            # work = summary.get('total_work_time', 0) or 0 # Removed in new schema
            ent = summary.get('total_entertainment_time', 0) or 0
            
            # total_prod = focus + work
            
            # New fields
            max_streak = summary.get('max_focus_streak', 0) or 0
            current_streak = summary.get('current_focus_streak', 0) or 0
            efficiency = summary.get('efficiency_score', 0) or 0
            
            return jsonify({
                "total_focus": focus,
                # "total_work": work, # Deprecated
                "total_entertainment": ent,
                "total_productive_seconds": focus, # Just focus now
                "max_focus_streak": max_streak,
                "current_focus_streak": current_streak,
                "efficiency_score": efficiency
            })
        except Exception as e:
            print(f"Error fetching stats: {e}")
            return jsonify({"error": str(e)}), 500

    # 示例：AI 生成日报接口
    @app.route('/api/generate_report', methods=['POST'])
    def generate_report():
        print("【Web服务】收到生成日报请求...")
        
        # 错峰执行：暂停后台 AI
        flag = app.config.get('AI_BUSY_FLAG')
        if flag:
            flag.value = True
            
        try:
            time.sleep(3) # 模拟 AI 思考
            return jsonify({"report": "今日专注效率很高，专注时长2小时..."})
        finally:
            # 恢复后台 AI
            if flag:
                flag.value = False

    @app.route('/api/chat', methods=['POST'])
    def chat_with_ai():
        data = request.json
        user_msg = data.get('message', '')
        if not user_msg:
            return jsonify({"error": "Empty message"}), 400

        print(f"【Web服务】收到聊天请求: {user_msg}")
        
        # 1. 错峰执行：设置忙碌标志
        flag = app.config.get('AI_BUSY_FLAG')
        if flag:
            flag.value = True
            
        try:
            # 2. 准备上下文 (RAG)
            # 获取最近的活动记录，让 AI 知道用户干了啥
            from app.data.dao.activity_dao import ActivityDAO
            from app.service.detector.detector_logic import analyze
            
            recent_activities = ActivityDAO.get_recent_activities(limit=20)
            context_str = ""
            if recent_activities:
                lines = []
                for act in recent_activities:
                    # 尝试获取友好的标题
                    title = act.get('summary') or "未知窗口"
                    if 'raw_data' in act and act['raw_data']:
                        try:
                            import json
                            rd = json.loads(act['raw_data'])
                            title = rd.get('window', title)
                        except: pass
                    
                    ts = act.get('timestamp')
                    lines.append(f"- [{ts}] {title} (状态: {act.get('status')})")
                context_str = "\n".join(lines)
            
            # 3. 构造 Prompt (仅用户部分)
            # 系统 Prompt 将通过参数传递，不再拼接在用户消息中
            
            system_prompt = f"""
            你是一个 Flow State 效率助手。用户正在询问关于他的工作/学习情况。
            以下是用户最近的活动记录（作为参考）：
            {context_str}
            
            请根据上述记录回答用户的问题。如果记录中没有相关信息，请诚实回答。
            保持回答简练、友好、有建设性。不要使用 JSON 格式回复，直接输出 Markdown 文本。
            """
            
            # 4. 调用 AI
            # 使用新版 analyze 接口，传入 system_prompt 并关闭 json_mode
            response_text = analyze(user_msg, system_prompt=system_prompt, json_mode=False)
            
            final_resp = response_text

            return jsonify({"response": final_resp})
            
        except Exception as e:
            print(f"【Web服务】聊天失败: {e}")
            return jsonify({"error": str(e)}), 500
        finally:
            # 5. 恢复后台 AI
            if flag:
                flag.value = False

    return app

def run_server(port=5000, ai_busy_flag=None):
    """
    启动 Web 服务器
    注意：在 PyQt 线程中运行时需要设置 use_reloader=False 避免二次启动
    """
    print(f"【Web服务进程】启动 (PID: {multiprocessing.current_process().pid}) http://127.0.0.1:{port}")
    try:
        app = create_app(ai_busy_flag)
        # use_reloader=False is crucial when running inside a thread/process from another app
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        print(f"【Web服务进程】启动失败: {e}")

if __name__ == '__main__':
    run_server()
