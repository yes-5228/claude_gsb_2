"""保洁巡查记录模型。"""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import InspectionResult, Shift
from app.core.database import Base


class Inspection(Base):
    """一次保洁巡查的结果，包含各检查项打分。"""

    __tablename__ = "inspections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restroom_id: Mapped[int] = mapped_column(
        ForeignKey("restrooms.id", ondelete="CASCADE"), index=True, comment="所属公厕"
    )
    inspector: Mapped[str] = mapped_column(String(60), index=True, comment="巡查人")
    inspect_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, index=True, comment="巡查时间"
    )
    shift: Mapped[str] = mapped_column(String(20), default=Shift.MORNING.value, comment="班次")
    items: Mapped[list[dict]] = mapped_column(JSON, default=list, comment="检查项打分明细")
    score: Mapped[float] = mapped_column(Float, default=0.0, comment="巡查得分")
    grade: Mapped[str] = mapped_column(String(20), default="", comment="评分等级")
    result: Mapped[str] = mapped_column(
        String(20), default=InspectionResult.NORMAL.value, index=True, comment="巡查结论"
    )
    # 环境卫生量化记录
    odor_level: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="异味等级")
    floor_condition: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="地面干湿情况"
    )
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True, comment="温度(℃)")
    humidity: Mapped[float | None] = mapped_column(Float, nullable=True, comment="相对湿度(%)")
    ventilation: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="通风状态"
    )
    disinfection_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="当日消杀频次(次/日)"
    )
    env_score: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="环境卫生评价分"
    )
    env_grade: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="环境卫生评价等级"
    )
    env_subscores: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="环境卫生各指标子分"
    )
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="巡查备注")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    restroom: Mapped["Restroom"] = relationship(back_populates="inspections")  # noqa: F821
    issues: Mapped[list["Issue"]] = relationship(back_populates="inspection")  # noqa: F821
