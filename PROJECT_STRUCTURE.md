# 项目结构：骁流 (Flow State)

本文档说明了代码库的组织结构，该结构采用了模块化和面向服务的架构。

## 目录树概览

```
c:/心境项目/flow_state/
├── app/                  # 主应用程序包
│   ├── core/             # 核心基础设施
│   │   ├── config.py     # 应用程序配置设置
│   │   └── ...
│   ├── data/             # 数据持久化层
│   │   ├── dao/          # 数据访问对象 (DAO)
│   │   │   ├── activity_dao.py # 活动日志 SQL 操作
│   │   │   ├── user_dao.py     # 用户 SQL 操作
│   │   │   └── ...
│   │   ├── base.py       # 数据库连接管理
│   │   ├── history.py    # 活动历史业务逻辑
│   │   └── ...
│   ├── 
│   │   ├── reminder/     # 提醒系统
│   │   │   ├── generator.py # 提醒内容生成
│   │   │   ├── manager.py   # 提醒管理器
│   │   │   └── ...services/         # 业务逻辑服务层
│   │   ├── ai/           # AI 相关服务
│   │   │   ├── inference.py # AI 推理逻辑
│   │   │   ├── vision.py    # 视觉处理逻辑
│   │   │   └── ...
│   │   ├── monitor_service.py # 监控后台线程
│   │   └── ...
│   └── ui/               # 用户界面层
│       ├── views/        # 视图控制器
│       │   ├── popup_view.py # 弹窗视图逻辑
│       │   └── ...
│       └── widgets/      # 可复用组件
│           ├── dialogs/  # 对话框组件
│           ├── report/   # 报表组件
│           ├── visuals/  # 视觉特效组件
│           ├── float_ball.py # 悬浮球
│           ├── focus_card.py # 专注卡片
│           └── ...
├── assets/               # 静态资源文件
├── focus_app.db          # SQLite 数据库文件
├── run.py                # 启动入口脚本
├── PROJECT_STRUCTURE.md  # 项目结构文档
└── TEAM_ROLES.md         # 团队分工文档
```

## 根目录
- `run.py`: 启动应用程序的入口脚本。
- `assets/`: 存储静态资源，如图像 (`focus_card.png` 等)。
- `app/`: 主应用程序包。

## 应用程序包 (`app/`)

### 核心 (`app/core/`)
包含核心基础设施代码。
- `config.py`: 应用程序配置设置。

### 服务 (`app/services/`)
包含业务逻辑和后台服务，与 UI 组件解耦。
- `monitor_service.py`: 摄像头监控的后台线程 (`MonitorThread`)。
- `ai/`: AI 相关服务。
  - `vision.py`: 图像处理和分析逻辑 (`CameraAnalyzer`)。
  - `inference.py`: 推理或调用外部 AI API 的逻辑。
- `reminder/`: 提醒系统逻辑。
  - `manager.py`: 管理提醒状态和触发器 (`EntertainmentReminder`)。
  - `generator.py`: 生成智能提醒内容。

### 数据 (`app/data/`)
处理数据持久化、数据库连接和模型。
- `base.py`: 数据库核心基础设施，负责连接管理和表结构初始化。
- `history.py`: 活动历史的**业务逻辑层**，负责状态流转和缓存。
- `dao/`: **数据访问对象 (DAO) 层**，封装所有 SQL 操作。
  - `activity_dao.py`: 活动日志、每日统计、OCR 记录的 SQL 操作。
  - `user_dao.py`: 用户注册、登录、查询的 SQL 操作。

### 用户界面 (`app/ui/`)
包含所有用户界面代码，按功能组织。

#### 视图 (`app/ui/views/`)
编排组件的高级控制器或主窗口。
- `popup_view.py`: 主弹出窗口逻辑 (`CardPopup`, `ImageOverlay`)。

#### 组件 (`app/ui/widgets/`)
可复用的 UI 组件。
- `float_ball.py`: 悬浮球组件。
- `focus_card.py`: 专注状态卡片组件。
- `history_report.py`: 用于显示历史记录入口的组件。

##### 对话框 (`app/ui/widgets/dialogs/`)
独立的对话框窗口。
- `tomato_clock.py`: 番茄钟计时对话框。
- `fatigue.py`: 疲劳提醒对话框。
- `reminder.py`: 简单提醒覆盖层。

##### 报告 (`app/ui/widgets/report/`)
详细报告的组件。
- `daily.py`: 日报总结。
- `weekly.py`: 周报仪表板。
- `monthly.py`: 月度里程碑报告。
- `theme.py`: 报告的 UI 主题。

##### 视觉效果 (`app/ui/widgets/visuals/`)
视觉增强组件（粒子、动画等）。
- `visual_effects_manager.py`
- `starry_envelope.py`
- ...以及其他。

## 关键架构说明
1.  **分层架构**：`Data Layer (DAO)` -> `Business Layer (Services/Managers)` -> `UI Layer`。
2.  **数据中心化**：所有数据库操作统一归拢到 `app/data`。
    - `base.py` 统一管理数据库连接 (`focus_app.db`)。
    - `dao/` 目录隔离了 SQL 语句，业务层看不到 SQL。
3.  **模块化**：`app` 包作为顶级命名空间，所有导入均使用绝对路径（如 `from app.data.dao.user_dao import UserDAO`）。
