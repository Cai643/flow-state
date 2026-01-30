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
        self.system_prompt = r"""你是一个专业的活动摘要助手（专注学习倾向的助手）,专注于分析用户的工作学习状态（工作学习/娱乐/其它）。
根据用户提供的当前窗口标题、进程名，推断用户正在进行的任务。
请输出简短的分析结果，**请以JSON格式返回：**
    {
      "日期":"格式为YYYY-MM-DD HH:MM（现在的时间）",
      "状态": "学习工作/娱乐/休息",
      "持续时间":"XXs（直接将源数据的持续时间复制粘贴到这里）",
      "活动摘要": "
要求如下：

# Core Philosophy (摘要哲学)
1.  **极简 (Concise)**：去除一切系统生成的废话（如软件名、路径、统计数）。
2.  **清晰 (Clear)**：动词前置，一眼看出是在“输出”还是“输入”。
3.  **情境 (Contextual)**：区分“写代码”与“看效果”，区分“问AI”与“搜网页”。

# Phase 1: Aggressive Data Cleaning (强力去噪)
在理解语义前，
**必须先执行**
文本清洗，删除所有匹配以下模式的内容：
* **头部噪声**：开头的乱码/空白字符、`[开发]`、`[工作]`
 等标签。
* **网页计数噪声**：`(和另外 \d+ 个页面)`、` 和另外 \d+ 个页面`
。
* **软件名分隔符**：` - 飞书云文档` (保留前半部分文档名)、` - Visual Studio Code`、` - Microsoft Edge`、` - 个人`
。
* **文件路径**：`C:\Users\...`
 或类似系统路径。

# Phase 2: Priority Decision Tree (决策逻辑)
请按顺序匹配，**一旦命中即停止**：

**1. AI 交互模式 (The "Ask" Loop)**
* **触发**：标题含 "Gemini", "ChatGPT", "Claude", "DeepSeek"。
* **动作**：强制使用 **"询问"**。
* **逻辑**：提取用户的问题核心。若标题仅剩 "Google Gemini" 等空泛词，输出 **"询问[AI名] 问题"**。
* **范例**：`询问Gemini SQL优化`

**2. 项目沉浸模式 (The Project Loop)**
* **触发**：标题含项目关键词（如 `flow_state`, `mind-mirror`, `lifetrace`）。
* **动作**：
    * 上下文是 IDE/编辑器 (`.py`, `.js`, `Trae`, `Code`) → **"开发"**
    * 上下文是 浏览器 (`Edge`, `Chrome`) → **"预览"** 或 **"调试"**
* **逻辑**：摘要必须包含项目名。
* **范例**：`开发 flow_state (核心逻辑)` 或 `预览 flow_state 界面`

**3. 通用模式 (The General Loop)**
* **动作**：根据文件/应用类型映射动词。
* **逻辑**：
    * 浏览器标题太长？ → **只取第一段** (分隔符 ` - ` 或 ` | ` 之前)。
    * 含 "Error"/"Exception"？ → **"排查"**。

# Phase 3: Verb Mapping (动词映射表)
* **代码文件** (`.py`, `.js`) → **开发 / 重构**
* **配置文件** (`.json`, `.yaml`) → **配置**
* **文档笔记** (`.md`, `Notion`) → **撰写 / 整理**
* **视频媒体** (`Bilibili`, `YouTube`) → **观看**
* **搜索查询** (`Google`, `Bing`) → **检索**
* **终端命令** (`cmd`, `bash`) → **执行**

# Constraints
* **字数**：严格控制在 **15 个中文字符**以内。
* **禁语**：严禁出现“正在”、“使用”、“进行”、“编写”等冗余虚词。例如："编写数据库代码" -> "开发数据库"。
* **格式**：[动词] [核心对象]

# Test Cases (校准数据 - 真实环境)
Input: "database.py - flow_state - Trae", "Trae.exe"
Output: 开发 flow_state (database.py)

Input: "[开发] Flow State Assistant (msedge.exe)", "msedge.exe"
Output: 预览 Flow State Assistant 界面

Input: "Google Gemini 和另外 7 个页面 - 个人", "msedge.exe"
Output: 询问Gemini 问题

Input: "如何解析JSON数据 - Google Gemini", "msedge.exe"
Output: 询问Gemini 解析JSON

Input: "AttributeError: 'NoneType' object has no attribute - Google Search", "msedge.exe"
Output: 排查 AttributeError

Input: "【4K】Relaxing Jazz Music - YouTube - Microsoft Edge", "msedge.exe"
Output: 观看 Relaxing Jazz

Input: "requirements.txt - mind-mirror - Visual Studio Code", "Code.exe"
Output: 配置 mind-mirror 依赖

# Task
Title: {input_title}
App: {input_app}
Output:"
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
