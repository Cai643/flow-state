import os
import datetime
import uuid
import json
import re

# 1. 强制不走代理（关键步骤！）
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
# 也可以尝试把 HTTP_PROXY 和 HTTPS_PROXY 清空，以防万一
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""

from app.service.ai.langflow_client import LangflowClient

class AIProcessor:
    def __init__(self):
        # 统一客户端（环境变量控制）
        self.client = LangflowClient()
        
        # 默认 System Prompt (保留作为文档，实际上现在通过 LangFlow 流程控制)
        self.system_prompt = """
你是专业用户活动总结助手，根据【窗口标题】【进程名】【持续时间】推断用户实际正在做的行为，并返回精炼的活动摘要。
**只允许用JSON返回结果，禁止其他任何词句；摘要必须精准反映窗口内容，不能输出“浏览网页”、“可能进行xx”等模板，也不能简单复述窗口标题原文。**

要求：
- 尽量推断出用户具体的活动内容，例如“查技术文档”、“在线购物”、“查学术资料”、“阅读新闻”、“收发邮件”等，不可输出“浏览网页”等泛泛答案。
- 若窗口标题含有具体网站、应用、操作动作，务必参考判断，摘要要尽可能细化。
- 不确定时优先猜测为“学习工作”（如查资料、技术、办公类页面等）；除非明确有娱乐、购物、休息等特征。
- 严禁输出“学习工作/娱乐”、“可能xx”等模糊描述。
- “活动摘要”不能直接粘贴输入内容，限20字以内。

输出示例（严格参照，禁止多字段或少字段）：
{
  "日期": "YYYY-MM-DD HH:MM",
  "状态": "学习工作/娱乐/休息",
  "持续时间": "XXs",
  "活动摘要": "具体活动简述，20字内"
}
"""

    def process(self, text, system_prompt=None, json_mode=True):
        # 获取当前实时时间
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 构造输入值
        # 注意：LangFlow 的 Input 组件通常只需要一个 input_value 字符串
        # 我们把 system_prompt 和 text 拼接起来，或者只传 text
        # 如果 system_prompt 很重要，最好将其硬编码在 LangFlow 的 Prompt 组件中
        # 这里我们将它们合并，以便 LangFlow 可以通过单一输入接收所有上下文
        
        # 优先使用传入的 system_prompt，否则使用默认的
        current_sys_prompt = system_prompt if system_prompt else self.system_prompt
        
        if current_sys_prompt:
            final_input = f"{current_sys_prompt}\n【当前系统时间】：{now_str}\n\nUser Input: {text}"
        else:
            final_input = f"【当前系统时间】：{now_str}\n\nUser Input: {text}"

        # Request payload configuration 
        payload = { 
            "output_type": "chat", 
            "input_type": "chat", 
            "input_value": final_input 
        } 
        payload["session_id"] = str(uuid.uuid4()) 
        
        try:
            result_text = self.client.call_flow('detector', final_input) or ''
            if json_mode:
                try:
                    json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                    if json_match:
                        clean_json_str = json_match.group(0)
                        json.loads(clean_json_str)
                        return clean_json_str
                except Exception:
                    pass
            return result_text

        except Exception as e:
            error_msg = f"Error making API request: {e}"
            print(error_msg)
            if json_mode:
                 return f'{{"error": "{error_msg}"}}'
            return error_msg
        

# 单例实例
ai_processor = AIProcessor()

def analyze(text, system_prompt=None, json_mode=True):
    return ai_processor.process(text, system_prompt, json_mode)

if __name__ == "__main__":
    while True:
        prompt = input("User：")
        print(analyze(prompt))
