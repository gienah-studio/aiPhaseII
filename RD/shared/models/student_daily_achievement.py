from sqlalchemy import Column, String, Integer, DateTime, Date, Numeric, Boolean, UniqueConstraint
from shared.database.session import Base
from datetime import datetime

class StudentDailyAchievement(Base):
    """学生每日达标记录表"""
    __tablename__ = "student_daily_achievement"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(Integer, nullable=False, comment="学生ID（userinfo.roleId）")
    student_name = Column(String(255), nullable=False, comment="学生姓名")
    achievement_date = Column(Date, nullable=False, index=True, comment="达标日期")
    daily_target = Column(Numeric(10, 2), nullable=False, default=50.00, comment="当日目标金额")
    completed_amount = Column(Numeric(10, 2), nullable=False, default=0.00, comment="当日完成金额（仅虚拟任务）")
    is_achieved = Column(Boolean, nullable=False, default=False, index=True, comment="是否达标：0-未达标，1-已达标")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")

    __table_args__ = (
        UniqueConstraint('student_id', 'achievement_date', name='uk_student_date'),
    )

    def __repr__(self):
        return f"<StudentDailyAchievement(student_id={self.student_id}, date={self.achievement_date}, achieved={self.is_achieved})>"