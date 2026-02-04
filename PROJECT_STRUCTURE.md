# 项目结构：骁流 (Flow State)

本文档说明了代码库的组织结构，该结构采用了模块化和面向服务的架构。

## 目录树概览

```
c:/心境项目/flow_state/
├── app/                  # 主应用程序包
│   ├── core/             # 核心基础设施
│   │   ├── config.py     # 应用程序配置设置
│   │   └── ...
│   ├── data/             # 数据持久化层 (Unified Data Access)
│   │   ├── __init__.py   # 统一导出接口
│   │   ├── core/         # 核心连接逻辑
│   │   │   └── database.py # 连接池与初始化
│   │   ├── dao/          # 数据访问对象 (DAO)
│   │   │   ├── storage/  # 数据库文件存储目录
│   │   │   │   └── focus_app.db
│   │   │   ├── activity_dao.py # 活动日志 SQL 操作
│   │   │   ├── analysis_dao.py # 数据分析 SQL 操作
│   │   │   ├── log_processor.py # 日志清洗逻辑 (ETL)
│   │   │   └── ...
│   │   ├── services/     # 数据业务逻辑
│   │   │   └── history_service.py # 活动历史管理
│   │   └── web_report/   # Web 报告生成逻辑
│   │       └── daily_report.py # 报告生成器
│   ├── scripts/          # 维护与分析脚本
│   │   ├── check_consistency.py # 检查数据库一致性
│   │   └── ...
│   ├── service/          # 业务逻辑服务层
│   │   ├── API/          # 后端 API 接口
│   │   │   └── web_API.py # Flask Web 服务
│   │   ├── ai/           # AI 相关服务 (LangFlow 集成)
│   │   ├── detector/     # 系统状态检测 (鼠标、键盘、焦点)
│   │   │   ├── detector_data.py  # 检测核心逻辑
│   │   │   └── detector_logic.py # AI 分析逻辑
│   │   └── monitor_service.py # 监控后台进程 (Worker)
│   ├── ui/               # 用户界面层 (PyQt/PySide)
│   │   ├── main.py       # UI 进程入口
│   │   ├── views/        # 视图控制器
│   │   └── widgets/      # 可复用组件
│   │       ├── component/ # 基础组件
│   │       ├── dialogs/   # 对话框组件
│   │       └── report/    # 报表组件
│   └── web/              # 网页端前端源码
│       ├── templates/    # HTML 模板
│       └── ...
├── run.py                # 启动入口脚本
├── PROJECT_STRUCTURE.md  # 项目结构文档
├── requirements.txt      # 依赖列表
└── TEAM_ROLES.md         # 团队分工文档
```

## 根目录
- `run.py`: 启动应用程序的入口脚本。
- `app/`: 主应用程序包.
- `requirements.txt`: Python 依赖包列表。

## 应用程序包 (`app/`)

### 核心 (`app/core/`)
包含核心基础设施代码。
- `config.py`: 应用程序配置设置。

### 服务 (`app/service/`)
包含业务逻辑和后台服务，与 UI 组件解耦。
- `monitor_service.py`: **AI 监控进程**。后台守护进程，负责采集数据、调用 AI 分析并写入数据库。
- `API/`: 提供 Web API 接口。
  - `web_API.py`: 提供给本地 Web 看板使用的 RESTful 接口。
- `ai/`: AI 集成服务，主要处理 LangFlow 通信。
- `detector/`: 系统行为检测服务。
  - `detector_data.py`: 负责监听鼠标、键盘和窗口焦点事件。
  - `detector_logic.py`: 包含对采集数据的 AI 分析逻辑。

### 脚本 (`app/scripts/`)
存放用于数据维护、分析和修复的独立脚本。
- `check_consistency.py`: 检查数据库一致性。
- `update_stats.py`: 手动更新统计数据。

### Web 前端 (`app/web/`)
包含本地网页版的源码。
- `templates/`: Flask 渲染的 HTML 入口文件。

### 数据 (`app/data/`)
处理数据持久化、数据库连接和模型。**所有外部调用必须通过 `app.data` 包导入，禁止直接引用子模块。**
- `__init__.py`: 统一导出接口。
- `core/database.py`: 数据库核心基础设施，配置数据库路径（指向 `dao/storage/`）。
- `services/history_service.py`: 活动历史的**业务逻辑层**，负责状态流转和缓存。
- `dao/`: **数据访问对象 (DAO) 层**，封装所有 SQL 操作。
  - `storage/`: 存放 SQLite 数据库文件 (`focus_app.db`, `cleaned_data.db`)。
  - `activity_dao.py`: 核心活动日志操作。
  - `log_processor.py`: 数据清洗与 ETL 逻辑。
- `web_report/`: 报告生成模块。
  - `daily_report.py`: 每日专注报告生成器。

### 用户界面 (`app/ui/`)
包含所有用户界面代码，按功能组织。基于 PySide6。
- `main.py`: **GUI 进程入口**。负责初始化 `QApplication` 和 `FlowStateApp` 管理器。

#### 视图 (`app/ui/views/`)
编排组件的高级控制器或主窗口。
- `popup_view.py`: 主悬浮窗/弹窗逻辑。

#### 组件 (`app/ui/widgets/`)
可复用的 UI 组件。
- `float_ball.py`: 桌面悬浮球。
- `focus_card.py`: 专注状态卡片。
- `screen_time_panel.py`: 屏幕时间统计面板。

##### 对话框 (`app/ui/widgets/dialogs/`)
独立的对话框窗口。
- `tomato_clock.py`: 番茄钟。
- `fatigue.py`: 疲劳提醒。
- `reminder.py`: 娱乐限时提醒。

##### 报告 (`app/ui/widgets/report/`)
详细报告的组件。
- `daily.py`: 日报总结界面。

## 关键架构说明
1.  **分层架构**：`Data Layer (DAO)` -> `Business Layer (Services)` -> `UI Layer`。
2.  **数据中心化**：数据库文件统一存储在 `app/data/dao/storage/`，所有数据库操作统一归拢到 `app/data`。
3.  **模块化**：`app` 包作为顶级命名空间，所有导入均使用绝对路径。
