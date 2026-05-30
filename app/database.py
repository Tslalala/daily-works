from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db():
    from app.models import target, habit, daily_log, activity_log  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # Migration: add suggested_date column if missing
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    if 'target_milestones' in inspector.get_table_names():
        cols = [c['name'] for c in inspector.get_columns('target_milestones')]
        if 'suggested_date' not in cols:
            with engine.connect() as conn:
                conn.execute(text('ALTER TABLE target_milestones ADD COLUMN suggested_date DATETIME'))
                conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
