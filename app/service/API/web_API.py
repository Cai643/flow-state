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

    # 新增：生成深度复盘报告接口 (Report Generation)
    @app.route('/api/report/generate', methods=['POST'])
    def generate_report_api():
        data = request.json
        days = data.get('days', 3)
        print(f"【Web服务】收到生成报告请求，周期: {days}天")
        
        # 错峰执行：设置忙碌标志
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
                print(f"【Web服务】实时提取失败: {e}")

            # 2. 准备数据和回调
            # 这里我们使用 remove_chat.py 中验证过的逻辑，直接调用 LangFlow API
            # 而不是使用本地的 detector_logic (因为 LangFlow 效果更好或用户指定)
            import requests
            import uuid
            
            # 配置 API (建议移至配置文件)
            API_KEY_1 = 'sk-Gwhx0iMED0qlkQS6Oxsuxo5DW192U-w28AM1JDEJsDk'
            URL_1 = "http://localhost:7860/api/v1/run/09733a7e-ecf8-4771-b3fd-d4a367d67f57"
            
            API_KEY_2 = 'sk-kidtu9j5hqYnpV5rGD81xvNPjQsq5QUmI53HY6JHp0M'
            URL_2 = "http://localhost:7860/api/v1/run/7886edbe-e56a-46b5-ae24-9103becf35f1"

            def call_langflow(url, key, text):
                try:
                    resp = requests.post(
                        url, 
                        json={"input_value": text, "input_type": "chat", "output_type": "chat", "session_id": str(uuid.uuid4())},
                        headers={"x-api-key": key},
                        timeout=30
                    )
                    resp.raise_for_status()
                    return resp.json()["outputs"][0]["outputs"][0]["results"]["message"]["text"]
                except Exception as e:
                    print(f"LangFlow API Error: {e}")
                    return None

            # 定义 AI 回调函数
            def ai_callback(context):
                print("【Web服务】正在请求 AI (LangFlow) 生成洞察...")
                
                # A. 生成核心事项 (Core Items)
                core_items = {}
                for log in context['daily_logs']:
                    date_str = log['date']
                    
                    # 获取多条目上下文
                    items_info = log.get('items_context', '')
                    # 兼容旧逻辑
                    if not items_info and log.get('top_app'):
                         items_info = f"[工作] {log['top_app']} - {log['title']}"

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
                    # 只有当有有效数据时才调用
                    if items_info and len(items_info) > 5:
                        print(f"  [AI] Generating summary for {date_str}...")
                        res = call_langflow(URL_1, API_KEY_1, prompt_event)
                        if res: 
                            print(f"  [AI] Result: {res}")
                            core_items[date_str] = res
                        else:
                            print(f"  [AI] Failed to get response for {date_str}")
                    else:
                        print(f"  [AI] Skip {date_str} (not enough info)")
                
                # B. 生成致追梦者 (深度总结 + 分析 + 建议)
                peak_info = context['peak_day']
                peak_str = f"{peak_info.get('date_str', '无')} ({peak_info.get('hours', 0)}h)"
                rows = context.get('period_stats_rows', [])
                top_apps = context.get('top_apps', '')
                
                # 简要聚合期内关键信息
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
                # 众数黄金时段
                from collections import Counter
                best_hour = 0
                if peak_hours:
                    best_hour = Counter(peak_hours).most_common(1)[0][0]
                avg_frag = round(sum(frag_vals)/len(frag_vals), 2) if frag_vals else 0
                avg_switch = round(sum(switch_vals)/len(switch_vals), 1) if switch_vals else 0
                summary_join = '；'.join(summaries[:3])  # 取前三天摘要

                # 口语化提示（人话）
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
                encouragement = call_langflow(URL_2, API_KEY_2, prompt_enc)
                if not encouragement:
                    encouragement = "AI 暂时繁忙，但数据见证了你的努力。继续加油！"

                return {
                    "core_items": core_items,
                    "encouragement": encouragement
                }

            # 生成报告
            generator = ReportGenerator()
            report_md = generator.generate_report(days=days, ai_callback=ai_callback)
            
            return jsonify({"report": report_md})
            
        except Exception as e:
            print(f"【Web服务】生成报告失败: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500
        finally:
            # 恢复后台 AI
            if flag:
                flag.value = False

    # 示例：AI 生成日报接口 (Old, kept for compatibility if needed)
    @app.route('/api/generate_report_old', methods=['POST'])
    def generate_report_old():
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
