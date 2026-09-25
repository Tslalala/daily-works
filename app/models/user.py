from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(30), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    overlay_style = Column(String(10), default="grid")  # grid / glass
    created_at = Column(DateTime, default=datetime.now)
