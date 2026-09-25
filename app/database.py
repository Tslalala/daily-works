from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db():
    from app.models import target, habit, daily_log, activity_log, user, session, work_clockin  # noqa: F401
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    # Migration: add suggested_date column if missing
    if 'target_milestones' in tables:
        cols = [c['name'] for c in inspector.get_columns('target_milestones')]
        if 'suggested_date' not in cols:
            with engine.connect() as conn:
                conn.execute(text('ALTER TABLE target_milestones ADD COLUMN suggested_date DATETIME'))
                conn.commit()

    # Migration (auth): add user_id to top-level tables if missing
    for table in ('targets', 'habits', 'activity_logs'):
        if table in tables:
            cols = [c['name'] for c in inspector.get_columns(table)]
            if 'user_id' not in cols:
                with engine.connect() as conn:
                    conn.execute(text(f'ALTER TABLE {table} ADD COLUMN user_id INTEGER'))
                    conn.execute(text(f'CREATE INDEX ix_{table}_user_id ON {table} (user_id)'))
                    conn.commit()

    # Migration: add habits.badge_style if missing (backfill deterministically by id)
    if 'habits' in tables:
        cols = [c['name'] for c in inspector.get_columns('habits')]
        if 'badge_style' not in cols:
            with engine.connect() as conn:
                conn.execute(text('ALTER TABLE habits ADD COLUMN badge_style VARCHAR(10)'))
                conn.execute(text('UPDATE habits SET badge_style = CAST((id % 8) + 1 AS TEXT)'))
                conn.commit()

    # Migration: add targets.badge_style if missing (backfill deterministically by id)
    if 'targets' in tables:
        cols = [c['name'] for c in inspector.get_columns('targets')]
        if 'badge_style' not in cols:
            with engine.connect() as conn:
                conn.execute(text('ALTER TABLE targets ADD COLUMN badge_style VARCHAR(10)'))
                conn.execute(text('UPDATE targets SET badge_style = CAST((id % 8) + 1 AS TEXT)'))
                conn.commit()

    # Migration: add users.overlay_style if missing
    if 'users' in tables:
        cols = [c['name'] for c in inspector.get_columns('users')]
        if 'overlay_style' not in cols:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN overlay_style VARCHAR(10) DEFAULT 'grid'"))
                conn.commit()

    # Migration (auth): daily_logs.log_date unique -> (user_id, log_date) composite
    if 'daily_logs' in tables:
        cols = [c['name'] for c in inspector.get_columns('daily_logs')]
        if 'user_id' not in cols:
            with engine.connect() as conn:
                conn.execute(text('''
                    CREATE TABLE daily_logs_new (
                        id INTEGER NOT NULL PRIMARY KEY,
                        user_id INTEGER,
                        log_date DATE NOT NULL,
                        content TEXT,
                        mood VARCHAR(20),
                        created_at DATETIME,
                        updated_at DATETIME,
                        UNIQUE (user_id, log_date)
                    )
                '''))
                conn.execute(text('''
                    INSERT INTO daily_logs_new (id, user_id, log_date, content, mood, created_at, updated_at)
                    SELECT id, NULL, log_date, content, mood, created_at, updated_at FROM daily_logs
                '''))
                conn.execute(text('DROP TABLE daily_logs'))
                conn.execute(text('ALTER TABLE daily_logs_new RENAME TO daily_logs'))
                conn.execute(text('CREATE INDEX ix_daily_logs_user_id ON daily_logs (user_id)'))
                conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
