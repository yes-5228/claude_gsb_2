"""字典接口：供前端下拉选项使用。"""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.constants import (
    ENV_DISINFECTION_IDEAL,
    ENV_DISINFECTION_MAX,
    ENV_DISINFECTION_MIN,
    ENV_HUMIDITY_IDEAL,
    ENV_HUMIDITY_MAX,
    ENV_HUMIDITY_MIN,
    ENV_REGRESSION_SCORE_DELTA,
    ENV_TEMPERATURE_IDEAL,
    ENV_TEMPERATURE_MAX,
    ENV_TEMPERATURE_MIN,
    FLOOR_SCORES,
    INSPECTION_CHECK_ITEMS,
    INSPECTION_ITEM_MAX_SCORE,
    ISSUE_TRANSITIONS,
    ODOR_SCORES,
    VENTILATION_SCORES,
    FloorCondition,
    IssueCategory,
    IssueSeverity,
    IssueStatus,
    OdorLevel,
    RestroomGrade,
    RestroomStatus,
    Shift,
    VentilationStatus,
)
from app.core.database import get_db
from app.services import inspection_service

router = APIRouter(prefix="/meta", tags=["字典"])


class RestroomOption(BaseModel):
    id: int
    code: str
    name: str
    district: str


class Dictionaries(BaseModel):
    restroom_status: list[str]
    restroom_grade: list[str]
    shift: list[str]
    issue_category: list[str]
    issue_severity: list[str]
    issue_status: list[str]
    inspection_check_items: list[str]
    inspection_item_max_score: int
    issue_transitions: dict[str, list[str]]
    odor_levels: list[str]
    floor_conditions: list[str]
    ventilation_statuses: list[str]
    env_limits: dict[str, float]
    env_subscore_rules: dict[str, dict[str, float]]


@router.get("/dictionaries", response_model=Dictionaries, summary="枚举字典")
def get_dictionaries() -> Dictionaries:
    return Dictionaries(
        restroom_status=[item.value for item in RestroomStatus],
        restroom_grade=[item.value for item in RestroomGrade],
        shift=[item.value for item in Shift],
        issue_category=[item.value for item in IssueCategory],
        issue_severity=[item.value for item in IssueSeverity],
        issue_status=[item.value for item in IssueStatus],
        inspection_check_items=list(INSPECTION_CHECK_ITEMS),
        inspection_item_max_score=INSPECTION_ITEM_MAX_SCORE,
        issue_transitions={key: list(value) for key, value in ISSUE_TRANSITIONS.items()},
        odor_levels=[item.value for item in OdorLevel],
        floor_conditions=[item.value for item in FloorCondition],
        ventilation_statuses=[item.value for item in VentilationStatus],
        env_limits={
            "temperature_min": float(ENV_TEMPERATURE_MIN),
            "temperature_max": float(ENV_TEMPERATURE_MAX),
            "humidity_min": float(ENV_HUMIDITY_MIN),
            "humidity_max": float(ENV_HUMIDITY_MAX),
            "disinfection_min": float(ENV_DISINFECTION_MIN),
            "disinfection_max": float(ENV_DISINFECTION_MAX),
            "temperature_ideal_low": float(ENV_TEMPERATURE_IDEAL[0]),
            "temperature_ideal_high": float(ENV_TEMPERATURE_IDEAL[1]),
            "humidity_ideal_low": float(ENV_HUMIDITY_IDEAL[0]),
            "humidity_ideal_high": float(ENV_HUMIDITY_IDEAL[1]),
            "disinfection_ideal": float(ENV_DISINFECTION_IDEAL),
            "regression_delta": float(ENV_REGRESSION_SCORE_DELTA),
        },
        env_subscore_rules={
            "odor": {key: float(value) for key, value in ODOR_SCORES.items()},
            "floor": {key: float(value) for key, value in FLOOR_SCORES.items()},
            "ventilation": {key: float(value) for key, value in VENTILATION_SCORES.items()},
        },
    )


@router.get("/restroom-options", response_model=list[RestroomOption], summary="公厕下拉选项")
def get_restroom_options(
    db: Annotated[Session, Depends(get_db)], keyword: str | None = None
) -> list[RestroomOption]:
    rows = inspection_service.restroom_options(db, keyword=keyword)
    return [
        RestroomOption(id=row.id, code=row.code, name=row.name, district=row.district)
        for row in rows
    ]
