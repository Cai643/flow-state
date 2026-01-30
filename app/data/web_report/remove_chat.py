import json
from datetime import date, timedelta
from report_generator import ReportGenerator
from app.service.ai.langflow_client import LangflowClient

client = LangflowClient()

def test_report_generation():
    print("🚀 开始测试报告生成流程...")
    
    # 1. 准备数据 (使用 ReportGenerator 的逻辑)
    # 我们只用它的数据获取部分，不直接生成报告
    generator = ReportGenerator()
    days = 3
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)
    
    print(f"📅 获取数据范围: {start_date} 至 {end_date}")
    data_context = generator._fetch_data(start_date, end_date)
    formatted = generator._process_data(data_context, days)
    
    # 2. 准备 "核心事件" 的 Prompts 并批量调用
    # 遍历每一天的日志
    core_items_result = {}
    print("\n🔍 开始生成每日核心事项...")
    
    for log in formatted["daily_logs_for_ai"]:
        # log 结构: {'date': '1月26日', 'top_app': 'Trae.exe', 'title': 'database.py', 'hours': 3.1}
        date_str = log['date']
        
        # 获取多条目上下文
        items_info = log.get('items_context', '')
        if not items_info and log.get('top_app'):
            items_info = f"[工作] {log['top_app']} - {log['title']}"

        # 构造 Prompt (Updated)
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
        # print(f"DEBUG PROMPT: {prompt_event}") # Debug
        print(f"  -> 正在处理 {date_str}...")
        summary = client.call_flow('summary', prompt_event)
        if summary:
            print(f"     ✅ AI总结: {summary}")
            core_items_result[date_str] = summary
        else:
            print("     ❌ 调用失败")

    # 3. 准备 "致奋斗者" 的 Prompt 并调用
    print("\n💌 开始生成致奋斗者寄语...")
    
    peak_info = formatted["peak_day_info"]
    peak_str = f"{peak_info.get('date_str', '无')} ({peak_info.get('hours', 0)}h)"
    
    prompt_encouragement = f"""
Role: 你是一个充满激情与同理心的高效能教练。
Task: 根据用户的专注数据，写一段“致奋斗者”的寄语。
- **拒绝套话**：不要写通用的鸡汤。每一句鼓励都必须有数据支撑。
- **引用细节**：一定要在文中提到具体的文件名、具体的时长（分钟数）或具体的时刻。
- **主要逻辑**：
    - 如果数据好：夸奖他的爆发力。
    - 如果数据看似一般（时长短或分数低）：夸奖他的坚持，解读出数据背后的“难处”（比如在做基础架构、在改Bug）。
- **语气风格**：像是多年的战友或观察者，深沉、懂他、有人情味。
Data Context:
- 专注总时长: {formatted['total_focus_hours']} 小时
- 意志力胜利: {formatted['willpower_wins']} 次 (意味着他战胜了诱惑)
- 巅峰时刻: {peak_str}
Style:
- 激昂、真诚、数据驱动。
- 必须引用上面的具体数字。
- 结尾要给人以力量。
- 字数控制在 100 字左右。
"""
    encouragement = client.call_flow('enc', prompt_encouragement)
    print(f"📝 AI寄语:\n{encouragement}")

    # 4. 模拟最终报告组装
    print("\n📊 最终报告预览 (部分):")
    print("-" * 30)
    for row in formatted["daily_rows_data"]:
        d = row['fmt_date']
        item = core_items_result.get(d, row['raw_core_item'])
        print(f"| {d} | {item} | {row['hours']}h |")
    print("-" * 30)
    print(f"致追梦者: {encouragement}")

if __name__ == "__main__":
    test_report_generation()
