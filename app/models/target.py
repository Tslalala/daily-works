from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text, Boolean, UniqueConstraint
from sqlalchemy import nullslast
from sqlalchemy.orm import relationship

from app.database import Base


class Target(Base):
    __tablename__ = "targets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    target_type = Column(String(20), nullable=False, default="short_term")  # deadline / long_term / short_term
    deadline = Column(DateTime, nullable=True)
    priority = Column(Integer, default=2)  # 1=高 2=中 3=低
    status = Column(String(20), default="active")  # active / completed / archived
    progress = Column(Integer, default=0)  # 0-100
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    milestones = relationship("TargetMilestone", back_populates="target", cascade="all, delete-orphan",
                              order_by=lambda: [nullslast(TargetMilestone.suggested_date), TargetMilestone.id])
    contributions = relationship("TargetContribution", back_populates="target", cascade="all, delete-orphan")


class TargetMilestone(Base):
    __tablename__ = "target_milestones"

    id = Column(Integer, primary_key=True, index=True)
    target_id = Column(Integer, ForeignKey("targets.id"), nullable=False)
    title = Column(String(200), nullable=False)
    suggested_date = Column(DateTime, nullable=True)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    sort_order = Column(Integer, default=0)

    target = relationship("Target", back_populates="milestones")


class TargetContribution(Base):
    __tablename__ = "target_contributions"

    id = Column(Integer, primary_key=True, index=True)
    target_id = Column(Integer, ForeignKey("targets.id"), nullable=False)
    log_date = Column(Date, nullable=False)
    content = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    target = relationship("Target", back_populates="contributions")

    __table_args__ = (
        UniqueConstraint("target_id", "log_date", name="uq_target_date"),
    )
