"""
专注力提升APP - 主程序
完整的API服务器，无依赖问题
"""

from flask import Flask, request, jsonify, g
from flask_cors import CORS
from functools import wraps
import jwt
import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import os
import re
import time
import platform
import subprocess
from dataclasses import dataclass, asdict


# ==================== 配置 ====================

class Config:
    """API配置"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
    DATABASE_PATH = 'focus_app.db'
    TOKEN_EXPIRATION_HOURS = 24
    API_VERSION = 'v1'
    HOST = '0.0.0.0'
    PORT = 5000
    DEBUG = True


# ==================== 数据模型 ====================

@dataclass
class MouseData:
    move_count: int = 0
    click_count: int = 0
    scroll_count: int = 0
    idle_time: float = 0
    move_distance: float = 0
    average_speed: float = 0
    click_interval: float = 0
    focused_area: str = ""


@dataclass
class KeyboardData:
    key_press_count: int = 0
    words_per_minute: float = 0
    typing_interval: float = 0
    backspace_rate: float = 0
    shortcut_usage: int = 0
    typing_rhythm: float = 0


@dataclass
class PageData:
    url: str = ""
    title:  str = ""
    content: str = ""
    app_name: str = ""
    domain: str = ""


@dataclass
class TimeData:
    session_duration: float = 0
    active_time: float = 0
    idle_time: float = 0
    time_of_day: int = 0
    day_of_week: int = 0
    consecutive_sessions: int = 0


@dataclass
class VideoLearningSignals:
    """视频学习信号"""
    is_video_playing: bool = False
    video_duration:  float = 0
    current_time: float = 0
    is_fullscreen: bool = False
    playback_speed: float = 1.0
    has_subtitles: bool = False
    has_paused: bool = False
    pause_frequency:  int = 0
    rewind_count: int = 0
    note_taking_detected: bool = False


@dataclass
class PageContentDetail:
    """页面内容详细信息"""
    window_title: str = ""
    app_name: str = ""
    url: str = ""
    domain: str = ""
    content_type: str = ""
    extracted_text: str = ""
    video_signals: Optional[VideoLearningSignals] = None
    metadata: Optional[Dict] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


# ==================== 跨平台窗口管理器 ====================

class CrossPlatformWindowManager:
    """跨平台窗口管理器"""
    
    def __init__(self):
        self.system = platform.system()
    
    def get_active_window_info(self) -> Tuple[str, str]:
        """
        获取活动窗口信息
        Returns:  (window_title, process_name)
        """
        if self.system == "Windows":
            return self._get_windows_active_window()
        elif self.system == "Darwin":  # macOS
            return self._get_macos_active_window()
        elif self.system == "Linux": 
            return self._get_linux_active_window()
        else:
            return "", ""
    
    def _get_windows_active_window(self) -> Tuple[str, str]:
        """Windows系统获取活动窗口"""
        try: 
            import ctypes
            
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            
            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            window_title = buff.value
            
            process_name = self._extract_app_from_title(window_title)
            
            return window_title, process_name
            
        except Exception as e:
            print(f"Windows窗口获取失败: {e}")
            return "", ""
    
    def _get_macos_active_window(self) -> Tuple[str, str]:
        """macOS系统获取活动窗口"""
        try:
            script = '''
            tell application "System Events"
                set frontApp to name of first application process whose frontmost is true
                set frontWindow to name of front window of application process frontApp
                return frontApp & "|" & frontWindow
            end tell
            '''
            
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                output = result.stdout. strip()
                if '|' in output:
                    process_name, window_title = output. split('|', 1)
                    return window_title, process_name
            
            return "", ""
            
        except Exception as e:
            print(f"macOS窗口获取失败: {e}")
            return "", ""
    
    def _get_linux_active_window(self) -> Tuple[str, str]:
        """Linux系统获取活动窗口"""
        try:
            result = subprocess.run(
                ['xdotool', 'getactivewindow', 'getwindowname'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result. returncode == 0:
                window_title = result.stdout. strip()
                process_name = ""
                return window_title, process_name
            
            return "", ""
            
        except Exception as e: 
            print(f"Linux窗口获取失败: {e}")
            return "", ""
    
    def _extract_app_from_title(self, title:  str) -> str:
        """从标题提取应用名"""
        if not title: 
            return ""
        
        browsers = {
            'Chrome': 'Google Chrome',
            'Firefox': 'Mozilla Firefox',
            'Edge': 'Microsoft Edge',
            'Safari': 'Safari',
            'Opera': 'Opera',
            'Brave':  'Brave'
        }
        
        for key, value in browsers.items():
            if key in title:
                return value
        
        if ' - ' in title:
            return title.split(' - ')[-1]. strip()
        elif '—' in title:
            return title. split('—')[-1].strip()
        
        return ""
    
    def get_all_window_titles(self) -> List[str]:
        """获取所有窗口标题"""
        if self.system == "Windows": 
            return self._get_windows_all_windows()
        return []
    
    def _get_windows_all_windows(self) -> List[str]:
        """Windows获取所有窗口"""
        try:
            import ctypes
            
            windows = []
            
            def callback(hwnd, extra):
                if ctypes.windll.user32.IsWindowVisible(hwnd):
                    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
                        windows. append(buff.value)
                return True
            
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes. POINTER(ctypes.c_int))
            ctypes.windll.user32.EnumWindows(WNDENUMPROC(callback), 0)
            
            return windows
            
        except: 
            return []


# ==================== 增强版页面识别器 ====================

class EnhancedPageRecognizer:
    """增强版页面识别器"""
    
    def __init__(self):
        self.window_manager = CrossPlatformWindowManager()
        self._init_patterns()
        
        self.last_window_title = ""
        self.window_switch_count = 0
        self. video_pause_history = []
    
    def _init_patterns(self):
        """初始化识别模式"""
        # 学习平台
        self.learning_platforms = [
            'coursera.org', 'edx.org', 'udemy.com', 'khanacademy.org',
            'bilibili.com/video', 'youtube.com/watch',
            'xuetangx.com', 'icourse163.org', 'mooc.study.163.com'
        ]
        
        # 学习关键词
        self.learning_keywords = [
            'tutorial', 'course', 'lesson', 'lecture', 'learning', 'education',
            'how to', 'learn', 'study', 'teach', 'training',
            '教程', '课程', '学习', '讲座', '培训', '教学', '入门', '精通'
        ]
        
        # 视频学习关键词
        self.video_learning_keywords = [
            '第', '集', 'episode', 'part', '完整版', 'full',
            '字幕', 'subtitle', '中英', '双语', '速成', '零基础'
        ]
        
        # 工作平台
        self.work_platforms = [
            'github.com', 'gitlab.com', 'jira.com', 'slack.com',
            'teams.microsoft.com', 'zoom.us', 'notion.so',
            'feishu.cn', 'dingtalk.com'
        ]
        
        # 工作关键词
        self. work_keywords = [
            'project', 'task', 'issue', 'meeting', 'dashboard',
            'client', 'report', '项目', '任务', '会议', '客户', '报告'
        ]
        
        # 娱乐/分心平台
        self.distraction_platforms = [
            'facebook.com', 'instagram. com', 'twitter.com', 'tiktok.com',
            'netflix.com', 'weibo.com', 'douyin.com',
            'taobao.com', 'jd.com', 'amazon.com'
        ]
        
        # 娱乐关键词
        self.distraction_keywords = [
            'entertainment', 'game', 'gaming', 'funny', 'meme',
            'shopping', 'shop', 'buy', '娱乐', '游戏', '购物', '搞笑'
        ]
    
    def recognize_page(self, detailed:  bool = False) -> PageContentDetail:
        """识别当前页面"""
        try:
            window_title, app_name = self.window_manager.get_active_window_info()
            
            if not window_title:
                return PageContentDetail()
            
            url, domain = self._extract_url_from_window(window_title)
            content_type = self._determine_content_type(window_title, url, app_name)
            
            video_signals = None
            if content_type == 'video' or self._is_video_platform(url):
                video_signals = self._analyze_video_learning(window_title, url)
            
            metadata = {
                'timestamp': datetime.now().isoformat(),
                'window_switch_count': self.window_switch_count
            }
            
            if window_title != self.last_window_title:
                self.window_switch_count += 1
                self.last_window_title = window_title
            
            return PageContentDetail(
                window_title=window_title,
                app_name=app_name,
                url=url,
                domain=domain,
                content_type=content_type,
                video_signals=video_signals,
                metadata=metadata
            )
            
        except Exception as e: 
            print(f"页面识别错误: {e}")
            return PageContentDetail()
    
    def _extract_url_from_window(self, window_title:  str) -> Tuple[str, str]:
        """从窗口标题提取URL"""
        url = ""
        domain = ""
        
        url_pattern = r'(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9-]+\.(com|org|net|cn|io))'
        match = re.search(url_pattern, window_title. lower())
        
        if match:
            url = match.group(0)
            domain = self._extract_domain(url)
        else:
            url, domain = self._infer_url_from_title(window_title)
        
        return url, domain
    
    def _extract_domain(self, url: str) -> str:
        """提取域名"""
        if not url:
            return ""
        
        url = re.sub(r'^https?://', '', url)
        url = re.sub(r'^www\.', '', url)
        parts = url.split('/')
        domain = parts[0] if parts else ""
        
        return domain
    
    def _infer_url_from_title(self, title: str) -> Tuple[str, str]:
        """从标题推断URL"""
        title_lower = title.lower()
        
        all_platforms = (self.learning_platforms + self.work_platforms + 
                        self.distraction_platforms)
        
        for platform in all_platforms:
            platform_name = platform.split('.')[0]
            if platform_name in title_lower: 
                return f"https://{platform}", platform
        
        return "", ""
    
    def _determine_content_type(self, window_title: str, url:  str, app_name: str) -> str:
        """判断内容类型"""
        text = f"{window_title} {url} {app_name}".lower()
        
        video_indicators = ['youtube', 'bilibili', 'video', '视频', 'watch', 'player']
        if any(indicator in text for indicator in video_indicators):
            return 'video'
        
        doc_indicators = ['pdf', 'doc', 'document', 'notion', 'evernote']
        if any(indicator in text for indicator in doc_indicators):
            return 'document'
        
        code_indicators = ['vscode', 'pycharm', 'code', 'editor']
        if any(indicator in text for indicator in code_indicators):
            return 'code'
        
        social_indicators = ['facebook', 'twitter', 'instagram', 'weibo']
        if any(indicator in text for indicator in social_indicators):
            return 'social'
        
        return 'webpage'
    
    def _is_video_platform(self, url: str) -> bool:
        """判断是否为视频平台"""
        if not url:
            return False
        
        video_domains = ['youtube.com', 'bilibili.com', 'vimeo.com', 
                        'coursera.org', 'udemy.com', 'netflix.com']
        
        return any(domain in url. lower() for domain in video_domains)
    
    def _analyze_video_learning(self, window_title: str, url: str) -> VideoLearningSignals:
        """分析视频学习信号"""
        signals = VideoLearningSignals()
        
        is_learning_video = self._is_learning_video(window_title, url)
        
        if not is_learning_video:
            return signals
        
        title_lower = window_title.lower()
        
        # 检测暂停
        if 'paused' in title_lower or '暂停' in title_lower:
            signals.has_paused = True
            self.video_pause_history.append(time.time())
        
        # 统计暂停频率
        recent_pauses = [t for t in self.video_pause_history if time.time() - t < 300]
        signals.pause_frequency = len(recent_pauses)
        
        # 提取视频时长和当前时间
        time_match = re.search(r'(\d+):(\d+)\s*/\s*(\d+):(\d+)', window_title)
        if time_match:
            current_min, current_sec, total_min, total_sec = map(int, time_match.groups())
            signals.current_time = current_min * 60 + current_sec
            signals.video_duration = total_min * 60 + total_sec
        
        # 检测播放速度
        speed_match = re.search(r'(\d+\.?\d*)x', window_title. lower())
        if speed_match: 
            signals.playback_speed = float(speed_match.group(1))
        
        # 检测字幕
        subtitle_indicators = ['字幕', 'subtitle', 'cc', '中英', '双语']
        signals.has_subtitles = any(ind in title_lower for ind in subtitle_indicators)
        
        # 检测笔记行为
        signals.note_taking_detected = self._detect_note_taking()
        
        signals.is_video_playing = not signals.has_paused
        
        return signals
    
    def _is_learning_video(self, window_title: str, url: str) -> bool:
        """判断是否为学习视频"""
        text = f"{window_title} {url}".lower()
        
        # 检查学习关键词
        has_learning_keyword = any(keyword in text for keyword in self.learning_keywords)
        has_video_keyword = any(keyword in text for keyword in self.video_learning_keywords)
        
        # 检查学习平台
        is_learning_platform = any(platform in text for platform in self.learning_platforms)
        
        # 排除娱乐关键词
        is_entertainment = any(keyword in text for keyword in self.distraction_keywords)
        
        return (has_learning_keyword or has_video_keyword or is_learning_platform) and not is_entertainment
    
    def _detect_note_taking(self) -> bool:
        """检测是否在记笔记"""
        try:
            all_windows = self.window_manager.get_all_window_titles()
            
            note_apps = ['notion', 'onenote', 'evernote', 'obsidian',
                        '记事本', 'notepad', 'markdown', 'word']
            
            for window_title in all_windows:
                if any(app in window_title. lower() for app in note_apps):
                    return True
            
            return False
        except:
            return False
    
    def analyze_page_for_focus(self, page_detail: PageContentDetail) -> Dict: 
        """分析页面对专注力的影响"""
        reasons = []
        focus_potential = 50
        distraction_risk = 50
        category = 'neutral'
        
        text = f"{page_detail.window_title} {page_detail. url} {page_detail.content_type}".lower()
        
        # 学习场景检测
        learning_score = 0
        
        for platform in self.learning_platforms:
            if platform in text:
                learning_score += 40
                reasons.append(f"检测到学习平台: {platform}")
                break
        
        for keyword in self.learning_keywords:
            if keyword in text:
                learning_score += 5
        
        # 视频学习特殊加分
        if page_detail.video_signals and page_detail.video_signals. is_video_playing:
            video = page_detail.video_signals
            
            if video.is_fullscreen:
                learning_score += 20
                reasons.append("全屏观看视频，专注度高")
            
            if video. has_subtitles:
                learning_score += 10
                reasons.append("开启字幕，认真学习")
            
            if video.note_taking_detected:
                learning_score += 25
                reasons.append("同时记笔记，学习效果好")
            
            if video.pause_frequency > 3:
                learning_score += 15
                reasons.append("频繁暂停思考，深度学习")
            
            if 1.25 <= video.playback_speed <= 1.5:
                learning_score += 10
                reasons.append("使用适当倍速，高效学习")
        
        # 工作场景检测
        work_score = 0
        
        for platform in self.work_platforms:
            if platform in text:
                work_score += 35
                reasons.append(f"检测到工作平台:  {platform}")
                break
        
        if page_detail.content_type == 'code':
            work_score += 40
            reasons.append("代码编辑器，专注工作")
        
        # 分心场景检测
        distraction_score = 0
        
        for platform in self.distraction_platforms:
            if platform in text:
                distraction_score += 45
                distraction_risk += 30
                reasons.append(f"⚠️ 娱乐/分心平台: {platform}")
                break
        
        # 确定类别
        scores: Dict[str, int] = {
            'learning': learning_score,
            'work': work_score,
            'distraction': distraction_score
        }
        
        max_score = max(scores.values())
        
        if max_score > 0:
            category = max(scores.keys(), key=lambda k: scores[k])
            confidence = max_score / (learning_score + work_score + distraction_score)
        else:
            category = 'neutral'
            confidence = 0.5
        
        # 计算专注潜力
        if category == 'learning' or category == 'work':
            focus_potential = min(50 + max_score, 100)
            distraction_risk = max(50 - max_score / 2, 0)
        elif category == 'distraction': 
            focus_potential = max(50 - max_score, 0)
            distraction_risk = min(50 + max_score, 100)
        
        return {
            'category':  category,
            'focus_potential': focus_potential,
            'distraction_risk': distraction_risk,
            'confidence': confidence,
            'reasons':  reasons,
            'scores': scores
        }


# ==================== 数据库管理 ====================

class DatabaseManager:
    """数据库管理器"""
    
    @staticmethod
    def get_db():
        """获取数据库连接"""
        if 'db' not in g: 
            g.db = sqlite3.connect(
                Config.DATABASE_PATH,
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            g.db.row_factory = sqlite3.Row
        return g.db
    
    @staticmethod
    def close_db(e=None):
        """关闭数据库连接"""
        db = g.pop('db', None)
        if db is not None:
            db.close()
    
    @staticmethod
    def init_db():
        """初始化数据库"""
        db = sqlite3.connect(Config.DATABASE_PATH)
        cursor = db.cursor()
        
        # 用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                settings TEXT
            )
        ''')
        
        # 活动记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activity_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                activity_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                focus_score REAL NOT NULL,
                page_data TEXT,
                mouse_data TEXT,
                keyboard_data TEXT,
                time_data TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # 专注度历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS focus_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                focus_score REAL NOT NULL,
                focus_level TEXT NOT NULL,
                activity TEXT NOT NULL,
                session_duration REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # 提醒记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reminder_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                reminder_type TEXT NOT NULL,
                message TEXT NOT NULL,
                priority TEXT NOT NULL,
                triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_response TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # 用户目标表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                goal_type TEXT NOT NULL,
                target_hours REAL,
                current_hours REAL DEFAULT 0,
                start_date DATE,
                end_date DATE,
                status TEXT DEFAULT 'active',
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # 行为事件表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS behavior_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                event_data TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        db.commit()
        db.close()
        print("[OK] 数据库初始化完成")


# ==================== Flask应用初始化 ====================

app = Flask(__name__)
app.config. from_object(Config)
CORS(app)

# 初始化页面识别器
page_recognizer = EnhancedPageRecognizer()

# ==================== 项目集成的轻量分析接口 ====================

_runtime_state = {
    'current_status': None,
    'status_started_at': None,
    'durations': {
        'entertainment': 0.0,
        'focus': 0.0,
        'reading': 0.0,
        'work': 0.0
    }
}

def _classify_status(monitor_data: Dict) -> str:
    change = float(monitor_data.get('screen_change_rate', 0.0) or 0.0)
    is_complex = bool(monitor_data.get('is_complex_scene', False))
    key_presses = int(monitor_data.get('key_presses', 0) or 0)
    mouse_clicks = int(monitor_data.get('mouse_clicks', 0) or 0)

    if change > 0.05 or is_complex:
        return 'entertainment'
    if key_presses + mouse_clicks >= 10:
        return 'work'
    if key_presses + mouse_clicks >= 3:
        return 'focus'
    return 'reading'

def _status_message(status: str) -> str:
    return {
        'entertainment': '检测到高动态画面，可能在娱乐/视频。',
        'work': '检测到较多输入操作，可能在工作。',
        'focus': '轻度输入且低动态，专注状态良好。',
        'reading': '静止画面为主，推测在阅读/思考。'
    }.get(status, '状态未知。')

def get_analysis(monitor_data: Dict) -> Dict:
    """供项目调用的轻量分析函数。
    输入: monitor_data = {key_presses, mouse_clicks, screen_change_rate, is_complex_scene}
    输出: {status, duration, message}
    """
    now = time.time()
    status = _classify_status(monitor_data)

    # 切换状态时重置起点
    if _runtime_state['current_status'] != status:
        _runtime_state['current_status'] = status
        _runtime_state['status_started_at'] = now

    # 更新持续时长
    started = _runtime_state['status_started_at'] or now
    duration = now - started
    _runtime_state['durations'][status] = duration

    return {
        'status': status,
        'duration': int(duration),
        'message': _status_message(status)
    }


# ==================== 认证中间件 ====================

def token_required(f):
    """Token验证装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({
                    'success': False,
                    'error': 'Token格式错误'
                }), 401
        
        if not token: 
            return jsonify({
                'success': False,
                'error': '缺少认证Token'
            }), 401
        
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user_id = data['user_id']
            
            db = DatabaseManager.get_db()
            cursor = db.cursor()
            cursor.execute('SELECT * FROM users WHERE id = ? ', (current_user_id,))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({
                    'success': False,
                    'error': '用户不存在'
                }), 401
            
            g.current_user_id = current_user_id
            
        except jwt.ExpiredSignatureError:
            return jsonify({
                'success': False,
                'error': 'Token已过期'
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                'success': False,
                'error':  '无效的Token'
            }), 401
        
        return f(*args, **kwargs)
    
    return decorated


# ==================== API路由 ====================

# ===== 认证相关 =====

@app. route(f'/api/{Config.API_VERSION}/auth/register', methods=['POST'])
def register():
    """用户注册"""
    try: 
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        email = data.get('email', '')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'error': '用户名和密码不能为空'
            }), 400
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        default_settings = {
            'doNotDisturb': False,
            'enableAllReminders': True,
            'workGoal': 8,
            'learningGoal': 2,
            'breakInterval': 25,
            'notificationSound': True
        }
        
        db = DatabaseManager.get_db()
        cursor = db.cursor()
        
        try:
            cursor.execute(
                'INSERT INTO users (username, password_hash, email, settings) VALUES (?, ?, ?, ?)',
                (username, password_hash, email, json. dumps(default_settings))
            )
            db.commit()
            user_id = cursor.lastrowid
            
            return jsonify({
                'success':  True,
                'message': '注册成功',
                'user_id': user_id
            }), 201
            
        except sqlite3.IntegrityError:
            return jsonify({
                'success':  False,
                'error': '用户名已存在'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success':  False,
            'error': str(e)
        }), 500


@app.route(f'/api/{Config.API_VERSION}/auth/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'error': '用户名和密码不能为空'
            }), 400
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        db = DatabaseManager.get_db()
        cursor = db.cursor()
        cursor.execute(
            'SELECT id, username FROM users WHERE username = ? AND password_hash = ?',
            (username, password_hash)
        )
        user = cursor.fetchone()
        
        if not user:
            return jsonify({
                'success': False,
                'error': '用户名或密码错误'
            }), 401
        
        token = jwt.encode({
            'user_id': user['id'],
            'username': user['username'],
            'exp': datetime.utcnow() + timedelta(hours=Config.TOKEN_EXPIRATION_HOURS)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            'success': True,
            'token': token,
            'user':  {
                'id': user['id'],
                'username': user['username']
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success':  False,
            'error': str(e)
        }), 500


# ===== 页面识别API =====

@app.route(f'/api/{Config.API_VERSION}/page/recognize', methods=['POST'])
@token_required
def recognize_current_page():
    """识别当前页面（增强版）"""
    try: 
        data = request.get_json()
        detailed = data.get('detailed', False)
        
        page_detail = page_recognizer.recognize_page(detailed=detailed)
        focus_analysis = page_recognizer.analyze_page_for_focus(page_detail)
        
        return jsonify({
            'success': True,
            'data': {
                'pageDetail': {
                    'windowTitle': page_detail.window_title,
                    'appName': page_detail.app_name,
                    'url':  page_detail.url,
                    'domain': page_detail.domain,
                    'contentType': page_detail.content_type,
                    'metadata': page_detail.metadata
                },
                'videoSignals': {
                    'isVideoPlaying': page_detail.video_signals.is_video_playing if page_detail.video_signals else False,
                    'videoDuration': page_detail.video_signals.video_duration if page_detail.video_signals else 0,
                    'currentTime': page_detail.video_signals.current_time if page_detail.video_signals else 0,
                    'isFullscreen': page_detail.video_signals.is_fullscreen if page_detail.video_signals else False,
                    'playbackSpeed': page_detail.video_signals.playback_speed if page_detail.video_signals else 1.0,
                    'hasSubtitles': page_detail.video_signals.has_subtitles if page_detail.video_signals else False,
                    'pauseFrequency': page_detail.video_signals.pause_frequency if page_detail.video_signals else 0,
                    'noteTaking': page_detail.video_signals.note_taking_detected if page_detail.video_signals else False
                } if page_detail.video_signals else None,
                'focusAnalysis': focus_analysis
            },
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"页面识别错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route(f'/api/{Config.API_VERSION}/video/learning-quality', methods=['POST'])
@token_required
def analyze_video_learning_quality():
    """分析视频学习质量"""
    try:
        data = request.get_json()
        video_signals_data = data.get('videoSignals', {})
        
        quality_score = calculate_video_learning_quality(video_signals_data)
        suggestions = generate_video_learning_suggestions(video_signals_data, quality_score)
        
        return jsonify({
            'success': True,
            'data': {
                'qualityScore': quality_score,
                'level': 'excellent' if quality_score >= 80 else 'good' if quality_score >= 60 else 'fair' if quality_score >= 40 else 'poor',
                'suggestions': suggestions
            }
        }), 200
        
    except Exception as e:
        print(f"视频学习质量分析错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ===== 辅助函数 =====

def calculate_video_learning_quality(video_signals:  Dict) -> float:
    """计算视频学习质量分数"""
    score = 50
    
    if video_signals.get('isFullscreen'):
        score += 20
    
    if video_signals.get('hasSubtitles'):
        score += 15
    
    if video_signals.get('noteTaking'):
        score += 25
    
    pause_freq = video_signals.get('pauseFrequency', 0)
    if 2 <= pause_freq <= 5:
        score += 10
    elif pause_freq > 5:
        score += 5
    
    speed = video_signals.get('playbackSpeed', 1.0)
    if 1.0 <= speed <= 1.5:
        score += 10
    elif speed > 2.0:
        score -= 10
    
    return min(score, 100)


def generate_video_learning_suggestions(video_signals: Dict, quality_score:  float) -> List[str]:
    """生成视频学习建议"""
    suggestions = []
    
    if quality_score < 60:
        suggestions.append("📝 建议边看边记笔记，加深理解")
    
    if not video_signals.get('isFullscreen'):
        suggestions.append("🖥️ 建议使用全屏模式，减少干扰")
    
    if not video_signals.get('hasSubtitles'):
        suggestions. append("📄 可以开启字幕，便于理解和复习")
    
    speed = video_signals.get('playbackSpeed', 1.0)
    if speed > 1.75:
        suggestions.append("⚠️ 播放速度较快，可能影响理解")
    
    if not video_signals.get('noteTaking'):
        suggestions.append("✍️ 强烈建议记笔记，学习效果会更好")
    
    if quality_score >= 80:
        suggestions.append("🎉 您的学习状态非常好，继续保持！")
    
    return suggestions


# ==================== Flask应用事件处理 ====================

@app. before_request
def before_request():
    """请求前处理"""
    g.request_start_time = datetime.now()


@app.after_request
def after_request(response):
    """请求后处理"""
    if hasattr(g, 'request_start_time'):
        elapsed = (datetime.now() - g.request_start_time).total_seconds()
        response.headers['X-Response-Time'] = f'{elapsed:.3f}s'
    return response


@app.teardown_appcontext
def teardown_db(exception):
    """清理数据库连接"""
    DatabaseManager.close_db(exception)


# ==================== 主程序入口 ====================

if __name__ == '__main__':
    # 初始化数据库
    DatabaseManager.init_db()
    
    title = "专注力提升APP - API服务器"
    lines = [
        f"API版本: {Config.API_VERSION}",
        f"运行地址: http://{Config.HOST}:{Config.PORT}",
        f"数据库: {Config.DATABASE_PATH}",
    ]

    # ASCII 版本方框，考虑中英文宽度（东亚宽字符按 2 计算）以避免不闭合
    import unicodedata

    def display_width(s: str) -> int:
        w = 0
        for ch in s:
            w += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
        return w

    content_width = max(display_width(title), *(display_width(ln) for ln in lines)) + 2  # 左右各留1空格
    top = "+" + "-" * content_width + "+"
    sep = "+" + "-" * content_width + "+"
    bottom = "+" + "-" * content_width + "+"

    def pad(line: str) -> str:
        padding = content_width - 1 - display_width(line)
        return " " + line + " " * max(0, padding)

    print(top)
    print("|" + pad(title) + "|")
    print(sep)
    for ln in lines:
        print("|" + pad(ln) + "|")
    print(bottom)
    
    # 启动Flask应用
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )