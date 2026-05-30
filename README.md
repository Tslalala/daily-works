# Daily Planner 📋

一个功能丰富的个人每日规划 Web 应用，支持目标管理、习惯打卡、AI 智能建议。

## ✨ 功能亮点

### 🎯 目标管理
- **三种目标类型**：有期限目标（带截止日期）、长期目标、短期目标
- **优先级设置**：高/中/低 三级优先级
- **进度追踪**：可视化进度条，里程碑自动计算完成度
- **拖拽排序**：目标列表支持拖拽调整顺序
- **每日贡献记录**：记录每天为每个目标做了什么，支持历史日期补录

### 🏆 里程碑系统
- 为每个目标设置关键里程碑节点
- 支持**行内编辑**：点击即可修改名称和日期
- 单个增删里程碑，灵活调整
- 完成里程碑自动推进目标进度

### 🤖 AI 智能建议（我最骄傲的功能！）
- **AI 目标分析**：输入标题，AI 自动生成目标描述、类型建议、截止日期建议和里程碑拆解
- **AI 建议优化**：对 AI 给出的建议不满意？输入补充说明，AI 会参考之前的建议重新生成
- **一键采纳**：AI 建议可直接采纳，自动创建或更新目标及其里程碑

### ✅ 习惯打卡
- 每日一键打卡，保持连续记录
- **连续天数统计**：查看每个习惯的坚持天数
- **打卡日历**：日历视图直观展示打卡历史，支持前后翻页
- **打卡备注**：每次打卡可附带文字备注

### 📊 仪表盘
- 临近截止目标一目了然
- 今日待打卡习惯提醒
- 今日活动日志时间线

### 🎨 界面主题
- 8 种配色主题自由切换（默认靛蓝、红色、绿色、橙色、紫色、粉色、深蓝、翠绿）
- Glassmorphism 毛玻璃设计风格

## 🛠 技术栈

| 技术 | 用途 |
|------|------|
| **FastAPI** | Python Web 框架 |
| **Jinja2** | 模板引擎 |
| **HTMX** | 前端交互（无需手写 JS） |
| **Alpine.js** | 前端状态管理 |
| **Tailwind CSS** (CDN) | 样式 |
| **SQLAlchemy 2.0** | ORM |
| **SQLite** | 数据库 |

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API 密钥（使用 AI 功能时需要）

在设置页面填写 API Key 和 API Base URL，或直接编辑 `.apikey` 文件：

```json
{"key": "your-api-key", "base": "https://api.deepseek.com"}
```

默认使用 DeepSeek API（兼容 OpenAI 格式），也可配置其他兼容的 API 服务。

### 3. 启动服务

```bash
python run.py
```

服务默认运行在 **http://localhost:8000**

### 4. 开机自启动（Windows）

```bash
python run.py --install    # 安装开机自启动
python run.py --uninstall  # 移除开机自启动
```

## 📁 项目结构

```
daily-works/
├── app/
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置（API 密钥管理）
│   ├── database.py          # 数据库连接
│   ├── models/              # SQLAlchemy 模型
│   ├── routers/             # 路由（页面 + API）
│   ├── schemas/             # Pydantic 数据模型
│   ├── services/            # 业务逻辑层
│   └── utils/               # 工具函数
├── templates/               # Jinja2 模板
│   ├── targets/             # 目标相关页面
│   ├── habits/              # 习惯相关页面
│   ├── daily_log/           # 每日日志页面
│   └── dashboard/           # 仪表盘
├── run.py                   # 启动脚本
├── seed.py                  # 种子数据
└── requirements.txt         # 依赖清单
```

## 📝 开源说明

本项目仅供个人学习使用。数据库文件 (`*.db`) 和 API 密钥文件 (`.apikey`) 已配置在 `.gitignore` 中，不会上传到 GitHub。
