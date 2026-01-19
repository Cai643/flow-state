import os
import datetime

# 1. 强制不走代理（关键步骤！）
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
# 也可以尝试把 HTTP_PROXY 和 HTTPS_PROXY 清空，以防万一
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""

import ollama

client = ollama.Client(host='http://127.0.0.1:11434')

# print(client.list())

# print(client.show('qwen2:7b'))

# print(client.ps())

class AIProcessor:
    def __init__(self):
        self.client = ollama.Client(host='http://127.0.0.1:11434')
        self.system_prompt = """你是一个专业的活动摘要助手（专注学习倾向的助手）,专注于分析用户的工作学习状态（工作学习/娱乐/其它）。
根据用户提供的当前窗口标题、进程名和持续时间，推断用户正在进行的任务。
请输出简短的分析结果，**请以JSON格式返回：**
    {
      "日期":"格式为YYYY-MM-DD HH:MM（现在的时间）",
      "状态": "学习工作/娱乐/休息",
      "持续时间":"XXs（直接将源数据的持续时间复制粘贴到这里）",
      "活动摘要": "结构化用户活动摘要（Markdown格式，不超过30字）"
    }"""

    def process(self, text, system_prompt=None, json_mode=True):
        # 获取当前实时时间
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        messages = []
        
        # 优先使用传入的 system_prompt，否则使用默认的
        current_sys_prompt = system_prompt if system_prompt else self.system_prompt
        
        if current_sys_prompt:
            # 将时间注入到 system prompt 中
            prompt_with_time = f"{current_sys_prompt}\n【当前系统时间】：{now_str}"
            messages.append({"role": "system", "content": prompt_with_time})
        
        messages.append({"role": "user", "content": text})

        try:
            # 只有在默认模式（后台监控）下才强制 JSON，聊天模式下不强制
            fmt = 'json' if json_mode else None
            
            response = self.client.chat(
                model='qwen2:7b',
                messages=messages,
                format=fmt 
            )
            return response['message']['content']
        except Exception as e:
            if json_mode:
                 return f'{{"error": "AI处理出错: {str(e)}"}}'
            else:
                 return f"AI处理出错: {str(e)}"

# 单例实例
ai_processor = AIProcessor()

def analyze(text, system_prompt=None, json_mode=True):
    return ai_processor.process(text, system_prompt, json_mode)

if __name__ == "__main__":
    while True:
        prompt = input("User：")
        print(analyze(prompt))