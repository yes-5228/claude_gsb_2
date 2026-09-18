"""环境卫生量化记录相关数据结构。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import (
    ODOR_LEVEL_MAX,
    ODOR_LEVEL_MIN,
    FloorCondition,
    VentilationStatus,
)
from app.schemas.restroom import RestroomBrief


class EnvironmentRecordCreate(BaseModel):
    restroom_id: int
    recorder: str = Field(min_length=1, max_length=60, description="记录人")
    record_time: datetime | None = Field(default=None, description="记录时间，留空取当前时间")
    odor_level: int = Field(
        ge=ODOR_LEVEL_MIN, le=ODOR_LEVEL_MAX, description="异味等级 0-3，越大越重"
    )
    floor_condition: FloorCondition = Field(
        default=FloorCondition.DRY, description="地面干湿情况"
    )
    temperature: float | None = Field(default=None, ge=-30, le=60, description="温度 ℃")
    humidity: float | None = Field(default=None, ge=0, le=100, description="湿度 %")
    ventilation: VentilationStatus = Field(
        default=VentilationStatus.GOOD, description="通风状态"
    )
    disinfection_count: int = Field(default=0, ge=0, le=20, description="当日消杀次数")
    remark: str | None = Field(default=None, max_length=500)


class EnvironmentRecordUpdate(BaseModel):
    recorder: str | None = Field(default=None, min_length=1, max_length=60)
    record_time: datetime | None = None
    odor_level: int | None = Field(default=None, ge=ODOR_LEVEL_MIN, le=ODOR_LEVEL_MAX)
    floor_condition: FloorCondition | None = None
    temperature: float | None = Field(default=None, ge=-30, le=60)
    humidity: float | None = Field(default=None, ge=0, le=100)
    ventilation: VentilationStatus | None = None
    disinfection_count: int | None = Field(default=None, ge=0, le=20)
    remark: str | None = Field(default=None, max_length=500)


class EnvironmentScorePart(BaseModel):
    """单项维度得分明细。"""

    key: str
    label: str
    value: str
    score: float
    max: float


class EnvironmentRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    restroom_id: int
    restroom: RestroomBrief | None = None
    recorder: str
    record_time: datetime
    odor_level: int
    odor_label: str = ""
    floor_condition: str
    temperature: float | None = None
    humidity: float | None = None
    ventilation: str
    disinfection_count: int
    score: float
    grade: str
    prev_score: float | None = None
    score_delta: float | None = None
    regressed: bool
    regress_reason: str | None = None
    remark: str | None = None
    created_at: datetime
    breakdown: list[EnvironmentScorePart] = Field(default_factory=list)


class EnvironmentTrendPoint(BaseModel):
    """同一公厕按时间排列的对比点。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    record_time: datetime
    score: float
    grade: str
    odor_level: int
    floor_condition: str
    ventilation: str
    disinfection_count: int
    score_delta: float | None = None
    regressed: bool


class EnvironmentTrend(BaseModel):
    """同一公厕的环境卫生时间序列与汇总。"""

    restroom: RestroomBrief
    record_count: int = 0
    latest_score: float | None = None
    latest_grade: str | None = None
    latest_regressed: bool = False
    avg_score: float | None = None
    points: list[EnvironmentTrendPoint] = Field(default_factory=list)
