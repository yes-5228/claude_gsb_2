"""保洁巡查记录相关数据结构。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import (
    ENV_DISINFECTION_MAX,
    ENV_DISINFECTION_MIN,
    ENV_HUMIDITY_MAX,
    ENV_HUMIDITY_MIN,
    ENV_TEMPERATURE_MAX,
    ENV_TEMPERATURE_MIN,
    FloorCondition,
    OdorLevel,
    Shift,
    VentilationStatus,
)
from app.schemas.restroom import RestroomBrief


class InspectionItem(BaseModel):
    """单个检查项的打分。"""

    name: str = Field(description="检查项名称")
    score: float = Field(ge=0, le=10, description="得分，0-10")
    remark: str | None = Field(default=None, max_length=200, description="单项备注")


class EnvironmentalMetrics(BaseModel):
    """巡查时登记的环境卫生量化指标。"""

    odor_level: OdorLevel = Field(description="异味等级")
    floor_condition: FloorCondition = Field(description="地面干湿情况")
    temperature: float = Field(
        ge=ENV_TEMPERATURE_MIN, le=ENV_TEMPERATURE_MAX, description="温度(℃)"
    )
    humidity: float = Field(ge=ENV_HUMIDITY_MIN, le=ENV_HUMIDITY_MAX, description="相对湿度(%)")
    ventilation: VentilationStatus = Field(description="通风状态")
    disinfection_count: int = Field(
        ge=ENV_DISINFECTION_MIN, le=ENV_DISINFECTION_MAX, description="当日消杀频次(次/日)"
    )


class InspectionCreate(BaseModel):
    restroom_id: int
    inspector: str = Field(min_length=1, max_length=60, description="巡查人")
    shift: Shift = Field(default=Shift.MORNING, description="班次")
    inspect_time: datetime | None = Field(default=None, description="巡查时间，留空取当前时间")
    items: list[InspectionItem] = Field(min_length=1, description="检查项打分明细")
    env: EnvironmentalMetrics | None = Field(default=None, description="环境卫生量化记录")
    remark: str | None = Field(default=None, max_length=500)


class InspectionUpdate(BaseModel):
    inspector: str | None = Field(default=None, max_length=60)
    shift: Shift | None = None
    inspect_time: datetime | None = None
    items: list[InspectionItem] | None = Field(default=None, min_length=1)
    env: EnvironmentalMetrics | None = Field(default=None, description="环境卫生量化记录")
    remark: str | None = Field(default=None, max_length=500)


class InspectionBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    inspector: str
    inspect_time: datetime
    score: float
    grade: str
    result: str
    shift: str
    env_score: float | None = None
    env_grade: str | None = None
    env_regressed: bool = False


class EnvironmentalOut(BaseModel):
    """环境卫生登记值与评价结果。"""

    odor_level: str
    floor_condition: str
    temperature: float
    humidity: float
    ventilation: str
    disinfection_count: int
    env_score: float
    env_grade: str
    subscores: dict[str, float] = Field(default_factory=dict)


class InspectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    restroom_id: int
    restroom: RestroomBrief | None = None
    inspector: str
    shift: str
    inspect_time: datetime
    items: list[InspectionItem] = Field(default_factory=list)
    score: float
    grade: str
    result: str
    env_score: float | None = None
    env_grade: str | None = None
    env: EnvironmentalOut | None = None
    # 与同一公厕上一次记录的时间对比结果
    env_regressed: bool = False
    prev_env_score: float | None = None
    prev_env_grade: str | None = None
    prev_inspect_time: datetime | None = None
    remark: str | None = None
    created_at: datetime
    issue_count: int = 0
