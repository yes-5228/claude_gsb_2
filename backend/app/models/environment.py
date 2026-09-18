"""环境卫生量化记录模型。"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import FloorCondition, VentilationStatus
from app.core.database import Base


class EnvironmentRecord(Base):
    """一次环境卫生量化记录：异味、地面、温湿度、通风与消杀情况。

    得分与评价等级由服务端按统一规则计算；regressed/regress_reason
    在与同一公厕上一条记录对比后写入，用于台账的退步标记。
    """

    __tablename__ = "environment_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restroom_id: Mapped[int] = mapped_column(
        ForeignKey("restrooms.id", ondelete="CASCADE"), index=True, comment="所属公厕"
    )
    recorder: Mapped[str] = mapped_column(String(60), index=True, comment="记录人")
    record_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, index=True, comment="记录时间"
    )
    odor_level: Mapped[int] = mapped_column(Integer, default=0, comment="异味等级 0-3")
    floor_condition: Mapped[str] = mapped_column(
        String(20), default=FloorCondition.DRY.value, comment="地面干湿情况"
    )
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True, comment="温度 ℃")
    humidity: Mapped[float | None] = mapped_column(Float, nullable=True, comment="湿度 %")
    ventilation: Mapped[str] = mapped_column(
        String(20), default=VentilationStatus.GOOD.value, comment="通风状态"
    )
    disinfection_count: Mapped[int] = mapped_column(Integer, default=0, comment="当日消杀次数")
    score: Mapped[float] = mapped_column(Float, default=0.0, comment="环境卫生得分")
    grade: Mapped[str] = mapped_column(String(20), default="", comment="环境卫生评价等级")
    prev_score: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="上一条记录得分"
    )
    score_delta: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="与上一条记录的得分差"
    )
    regressed: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True, comment="是否明显退步"
    )
    regress_reason: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="退步原因说明"
    )
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    restroom: Mapped["Restroom"] = relationship(back_populates="environment_records")  # noqa: F821
