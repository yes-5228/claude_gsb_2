"""环境卫生量化记录业务逻辑。"""

from datetime import date, datetime, time

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models import EnvironmentRecord, Restroom
from app.schemas.environment import (
    EnvironmentRecordCreate,
    EnvironmentRecordOut,
    EnvironmentRecordUpdate,
    EnvironmentScorePart,
    EnvironmentTrend,
    EnvironmentTrendPoint,
)
from app.services import env_scoring, restroom_service
from app.services.env_scoring import detect_regression, evaluate_env, score_breakdown

SORTABLE_FIELDS = {
    "record_time": EnvironmentRecord.record_time,
    "score": EnvironmentRecord.score,
    "recorder": EnvironmentRecord.recorder,
    "created_at": EnvironmentRecord.created_at,
}


def get_record(db: Session, record_id: int) -> EnvironmentRecord:
    record = db.get(EnvironmentRecord, record_id)
    if record is None:
        raise NotFoundError(f"环境卫生记录 {record_id} 不存在")
    return record


def to_out(record: EnvironmentRecord) -> EnvironmentRecordOut:
    data = EnvironmentRecordOut.model_validate(record)
    data.odor_label = env_scoring.odor_label(record.odor_level)
    data.breakdown = [
        EnvironmentScorePart(**part)
        for part in score_breakdown(
            odor_level=record.odor_level,
            floor_condition=record.floor_condition,
            temperature=record.temperature,
            humidity=record.humidity,
            ventilation=record.ventilation,
            disinfection_count=record.disinfection_count,
        )
    ]
    return data


def list_records(
    db: Session,
    *,
    restroom_id: int | None = None,
    district: str | None = None,
    recorder: str | None = None,
    grade: str | None = None,
    regressed: bool | None = None,
    keyword: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "record_time",
    order: str = "desc",
) -> tuple[list[EnvironmentRecord], int]:
    stmt = select(EnvironmentRecord)
    if district:
        stmt = stmt.join(Restroom, Restroom.id == EnvironmentRecord.restroom_id).where(
            Restroom.district == district
        )
    if restroom_id:
        stmt = stmt.where(EnvironmentRecord.restroom_id == restroom_id)
    if recorder:
        stmt = stmt.where(EnvironmentRecord.recorder.like(f"%{recorder.strip()}%"))
    if grade:
        stmt = stmt.where(EnvironmentRecord.grade == grade)
    if regressed is not None:
        stmt = stmt.where(EnvironmentRecord.regressed.is_(regressed))
    if date_from:
        stmt = stmt.where(EnvironmentRecord.record_time >= datetime.combine(date_from, time.min))
    if date_to:
        stmt = stmt.where(EnvironmentRecord.record_time <= datetime.combine(date_to, time.max))
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(
            or_(
                EnvironmentRecord.recorder.like(like),
                EnvironmentRecord.remark.like(like),
                EnvironmentRecord.restroom_id.in_(
                    select(Restroom.id).where(Restroom.name.like(like))
                ),
            )
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    column = SORTABLE_FIELDS.get(sort_by, EnvironmentRecord.record_time)
    stmt = stmt.order_by(
        column.desc() if order == "desc" else column.asc(), EnvironmentRecord.id.desc()
    )
    rows = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)))
    return rows, total


def _apply_evaluation(record: EnvironmentRecord) -> None:
    record.score, record.grade = evaluate_env(
        odor_level=record.odor_level,
        floor_condition=record.floor_condition,
        temperature=record.temperature,
        humidity=record.humidity,
        ventilation=record.ventilation,
        disinfection_count=record.disinfection_count,
    )


def _apply_comparison(db: Session, record: EnvironmentRecord) -> None:
    """与同一公厕时间上一条记录对比，写入得分差与退步标记。"""
    previous = db.scalars(
        select(EnvironmentRecord)
        .where(
            EnvironmentRecord.restroom_id == record.restroom_id,
            or_(
                EnvironmentRecord.record_time < record.record_time,
                and_(
                    EnvironmentRecord.record_time == record.record_time,
                    EnvironmentRecord.id < record.id,
                ),
            ),
        )
        .order_by(EnvironmentRecord.record_time.desc(), EnvironmentRecord.id.desc())
        .limit(1)
    ).first()
    if previous is None:
        record.prev_score = None
        record.score_delta = None
        record.regressed = False
        record.regress_reason = None
        return
    record.prev_score = previous.score
    record.score_delta = round(record.score - previous.score, 1)
    record.regressed, record.regress_reason = detect_regression(
        prev_score=previous.score,
        prev_odor_level=previous.odor_level,
        score=record.score,
        odor_level=record.odor_level,
    )


def create_record(db: Session, payload: EnvironmentRecordCreate) -> EnvironmentRecord:
    restroom_service.get_restroom(db, payload.restroom_id)
    record = EnvironmentRecord(
        restroom_id=payload.restroom_id,
        recorder=payload.recorder,
        record_time=payload.record_time or datetime.now(),
        odor_level=payload.odor_level,
        floor_condition=(
            payload.floor_condition.value
            if hasattr(payload.floor_condition, "value")
            else payload.floor_condition
        ),
        temperature=payload.temperature,
        humidity=payload.humidity,
        ventilation=(
            payload.ventilation.value
            if hasattr(payload.ventilation, "value")
            else payload.ventilation
        ),
        disinfection_count=payload.disinfection_count,
        remark=payload.remark,
    )
    _apply_evaluation(record)
    db.add(record)
    db.flush()  # 先拿到 id，再与历史记录对比
    _apply_comparison(db, record)
    db.commit()
    db.refresh(record)
    restroom_service.touch(db, payload.restroom_id)
    return record


def update_record(
    db: Session, record_id: int, payload: EnvironmentRecordUpdate
) -> EnvironmentRecord:
    record = get_record(db, record_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(record, key, value.value if hasattr(value, "value") else value)
    _apply_evaluation(record)
    _apply_comparison(db, record)
    db.commit()
    db.refresh(record)
    restroom_service.touch(db, record.restroom_id)
    return record


def delete_record(db: Session, record_id: int) -> None:
    record = get_record(db, record_id)
    db.delete(record)
    db.commit()


def latest_by_restrooms(db: Session, restroom_ids: list[int]) -> dict[int, EnvironmentRecord]:
    """每个公厕取记录时间最新的一条环境卫生记录。"""
    if not restroom_ids:
        return {}
    stmt = (
        select(EnvironmentRecord)
        .where(EnvironmentRecord.restroom_id.in_(restroom_ids))
        .order_by(EnvironmentRecord.record_time.desc(), EnvironmentRecord.id.desc())
    )
    latest: dict[int, EnvironmentRecord] = {}
    for record in db.scalars(stmt):
        latest.setdefault(record.restroom_id, record)
    return latest


def get_trend(db: Session, restroom_id: int) -> EnvironmentTrend:
    restroom = restroom_service.get_restroom(db, restroom_id)
    records = list(
        db.scalars(
            select(EnvironmentRecord)
            .where(EnvironmentRecord.restroom_id == restroom_id)
            .order_by(EnvironmentRecord.record_time.asc(), EnvironmentRecord.id.asc())
        )
    )
    points = [EnvironmentTrendPoint.model_validate(record) for record in records]
    latest = records[-1] if records else None
    avg = round(sum(item.score for item in points) / len(points), 1) if points else None
    return EnvironmentTrend(
        restroom=restroom,
        record_count=len(points),
        latest_score=latest.score if latest else None,
        latest_grade=latest.grade if latest else None,
        latest_regressed=bool(latest.regressed) if latest else False,
        avg_score=avg,
        points=points,
    )
