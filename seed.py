"""Seed script to populate the database with sample data."""
from datetime import date, datetime, timedelta

from app.database import SessionLocal, init_db
from app.models.target import Target, TargetMilestone
from app.models.habit import Habit, CheckIn
from app.models.daily_log import DailyLog


def seed():
    init_db()
    db = SessionLocal()

    try:
        # Clear existing data
        db.query(CheckIn).delete()
        db.query(Habit).delete()
        db.query(TargetMilestone).delete()
        db.query(Target).delete()
        db.query(DailyLog).delete()
        db.commit()

        # --- Targets ---
        t1 = Target(
            title="硕士毕业论文PPT答辩",
            description="完成PPT制作并熟练掌握答辩内容",
            target_type="deadline",
            deadline=datetime(2026, 5, 21, 14, 0),
            priority=1,
            progress=40,
        )
        t2 = Target(
            title="搭建每日规划器应用",
            description="用 Python + FastAPI 完成每日规划器的开发",
            target_type="short_term",
            priority=2,
            progress=0,
        )
        t3 = Target(
            title="学习吉他",
            description="系统学习吉他演奏，从基础和弦开始",
            target_type="long_term",
            priority=3,
            progress=15,
        )

        db.add_all([t1, t2, t3])
        db.flush()

        # Milestones for t1
        db.add_all([
            TargetMilestone(target_id=t1.id, title="完成PPT初稿", sort_order=1),
            TargetMilestone(target_id=t1.id, title="模拟答辩练习", sort_order=2),
            TargetMilestone(target_id=t1.id, title="最终修改定稿", sort_order=3),
        ])

        # --- Habits ---
        h1 = Habit(name="每日健身", description="保持身体健康", icon="💪")
        h2 = Habit(name="Duolingo 英语", description="每天学一点英语", icon="📖")
        h3 = Habit(name="冥想", description="放松身心，专注当下", icon="🧘")

        db.add_all([h1, h2, h3])
        db.flush()

        # Recent check-ins for h1 (continuous streak)
        today = date.today()
        for i in range(10):
            d = today - timedelta(days=i)
            db.add(CheckIn(habit_id=h1.id, checkin_date=d))

        # Recent check-ins for h2 (sporadic)
        for i in [1, 3, 4, 7, 8]:
            d = today - timedelta(days=i)
            db.add(CheckIn(habit_id=h2.id, checkin_date=d))

        # --- Daily Logs ---
        db.add_all([
            DailyLog(log_date=today, content="今天是充实的一天，开始了每日规划器的开发。", mood="good"),
            DailyLog(log_date=today - timedelta(days=1), content="准备答辩材料，进度还差一些。", mood="neutral"),
        ])

        db.commit()
        print(f"[OK] Seed data inserted successfully!")
        print(f"   Targets: {db.query(Target).count()}")
        print(f"   Habits: {db.query(Habit).count()}")
        print(f"   CheckIns: {db.query(CheckIn).count()}")
        print(f"   DailyLogs: {db.query(DailyLog).count()}")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
