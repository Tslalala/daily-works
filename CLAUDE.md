  ## 技术栈
  FastAPI + Jinja2 + HTMX + Alpine.js + Tailwind CSS (CDN) + SQLAlchemy 2.0 + SQLite + Pydantic v2

  ## 核心功能
  1. 两种目标：带截止日期 / 无截止日期（长期/短期）+ 优先级
  2. 每日打卡：习惯管理 + 一键打卡 + 打卡历史
  3. 仪表盘：临近截止 + 今日待打卡 + 整体进度

  ## 数据库表
  targets, target_milestones, habits, checkins, daily_logs

  ## 路由架构
  页面路由 → 完整HTML | HTMX API → HTML片段 | Mobile API → JSON

  ## 6阶段实施
  1. 项目骨架 2. 数据库模型 3. 目标CRUD 4. 习惯打卡 5. 仪表盘 6. 打磨扩展
  EOF

