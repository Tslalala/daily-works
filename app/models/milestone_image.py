from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class MilestoneImage(Base):
    __tablename__ = "milestone_images"

    id = Column(Integer, primary_key=True, index=True)
    milestone_id = Column(Integer, ForeignKey("target_milestones.id"), nullable=False, index=True)
    # Relative path under the uploads/ root: user_{id}/{uuid}.{ext}
    filename = Column(String(120), nullable=False)
    content_type = Column(String(50), nullable=False, default="image/jpeg")
    size = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)

    milestone = relationship("TargetMilestone", back_populates="images")
