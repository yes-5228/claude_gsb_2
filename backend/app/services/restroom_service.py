"""公厕台账业务逻辑。"""

from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.constants import OPEN_ISSUE_STATUSES
from app.core.exceptions import ConflictError, DomainError, NotFoundError
from app.models import EnvironmentRecord, Inspection, Issue, Restroom
from app.schemas.restroom import RestroomCreate, RestroomDetail, RestroomOut, RestroomUpdate

SORTABLE_FIELDS = {
    "code": Restroom.code,
    "name": Restroom.name,
    "district": Restroom.district,
    "created_at": Restroom.created_at,
    "updated_at": Restroom.updated_at,
}


def _next_code(db: Session) -> str:
    """生成形如 WC-0007 的公厕编号。"""
    seq = (db.scalar(select(func.count()).select_from(Restroom)) or 0) + 1
    while True:
        code = f"WC-{seq:04d}"
        if not db.scalar(select(Restroom.id).where(Restroom.code == code)):
            return code
        seq += 1


def get_restroom(db: Session, restroom_id: int) -> Restroom:
    restroom = db.get(Restroom, restroom_id)
    if restroom is None:
        raise NotFoundError(f"公厕 {restroom_id} 不存在")
    return restroom


def list_restrooms(
    db: Session,
    *,
    keyword: str | None = None,
    district: str | None = None,
    status: str | None = None,
    grade: str | None = None,
    env_regressed: bool | None = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "created_at",
    order: str = "desc",
) -> tuple[list[Restroom], int]:
    stmt = select(Restroom)
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(
            or_(
                Restroom.name.like(like),
                Restroom.code.like(like),
                Restroom.address.like(like),
                Restroom.manager.like(like),
            )
        )
    if district:
        stmt = stmt.where(Restroom.district == district)
    if status:
        stmt = stmt.where(Restroom.status == status)
    if grade:
        stmt = stmt.where(Restroom.grade == grade)
    if env_regressed is not None:
        ids = _regressed_env_restroom_ids()
        stmt = stmt.where(Restroom.id.in_(ids) if env_regressed else Restroom.id.notin_(ids))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    column = SORTABLE_FIELDS.get(sort_by, Restroom.created_at)
    stmt = stmt.order_by(column.desc() if order == "desc" else column.asc(), Restroom.id.desc())
    rows = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)))
    return rows, total


def _regressed_env_restroom_ids():
    """最新一条环境卫生记录被标记为明显退步的公厕 id 子查询。"""
    latest = (
        select(
            EnvironmentRecord.restroom_id.label("restroom_id"),
            func.max(EnvironmentRecord.record_time).label("max_time"),
        )
        .group_by(EnvironmentRecord.restroom_id)
        .subquery()
    )
    return (
        select(EnvironmentRecord.restroom_id)
        .join(
            latest,
            (EnvironmentRecord.restroom_id == latest.c.restroom_id)
            & (EnvironmentRecord.record_time == latest.c.max_time),
        )
        .where(EnvironmentRecord.regressed.is_(True))
    )


def list_districts(db: Session) -> list[str]:
    return list(db.scalars(select(Restroom.district).distinct().order_by(Restroom.district)))


def create_restroom(db: Session, payload: RestroomCreate) -> Restroom:
    data = payload.model_dump()
    code = (data.pop("code") or "").strip() or _next_code(db)
    if db.scalar(select(Restroom.id).where(Restroom.code == code)):
        raise DomainError(f"公厕编号 {code} 已存在")
    data = {key: (value.value if hasattr(value, "value") else value) for key, value in data.items()}
    restroom = Restroom(code=code, **data)
    db.add(restroom)
    db.commit()
    db.refresh(restroom)
    return restroom


def update_restroom(db: Session, restroom_id: int, payload: RestroomUpdate) -> Restroom:
    restroom = get_restroom(db, restroom_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(restroom, key, value.value if hasattr(value, "value") else value)
    db.commit()
    db.refresh(restroom)
    return restroom


def delete_restroom(db: Session, restroom_id: int, *, force: bool = False) -> None:
    restroom = get_restroom(db, restroom_id)
    inspection_count = db.scalar(
        select(func.count()).select_from(Inspection).where(Inspection.restroom_id == restroom_id)
    ) or 0
    issue_count = db.scalar(
        select(func.count()).select_from(Issue).where(Issue.restroom_id == restroom_id)
    ) or 0
    env_count = db.scalar(
        select(func.count())
        .select_from(EnvironmentRecord)
        .where(EnvironmentRecord.restroom_id == restroom_id)
    ) or 0
    if (inspection_count or issue_count or env_count) and not force:
        raise ConflictError(
            f"该公厕已有 {inspection_count} 条巡查记录、{issue_count} 条问题记录、"
            f"{env_count} 条环境卫生记录，确需删除请使用 force=true"
        )
    db.delete(restroom)
    db.commit()


def get_restroom_detail(db: Session, restroom_id: int) -> RestroomDetail:
    restroom = get_restroom(db, restroom_id)
    inspection_count = db.scalar(
        select(func.count()).select_from(Inspection).where(Inspection.restroom_id == restroom_id)
    ) or 0
    avg_score = db.scalar(
        select(func.avg(Inspection.score)).where(Inspection.restroom_id == restroom_id)
    )
    latest = db.scalars(
        select(Inspection)
        .where(Inspection.restroom_id == restroom_id)
        .order_by(Inspection.inspect_time.desc(), Inspection.id.desc())
        .limit(1)
    ).first()
    open_issue_count = db.scalar(
        select(func.count())
        .select_from(Issue)
        .where(Issue.restroom_id == restroom_id, Issue.status.in_(OPEN_ISSUE_STATUSES))
    ) or 0
    total_issue_count = db.scalar(
        select(func.count()).select_from(Issue).where(Issue.restroom_id == restroom_id)
    ) or 0
    env_record_count = db.scalar(
        select(func.count())
        .select_from(EnvironmentRecord)
        .where(EnvironmentRecord.restroom_id == restroom_id)
    ) or 0
    latest_env = db.scalars(
        select(EnvironmentRecord)
        .where(EnvironmentRecord.restroom_id == restroom_id)
        .order_by(EnvironmentRecord.record_time.desc(), EnvironmentRecord.id.desc())
        .limit(1)
    ).first()

    base = RestroomOut.model_validate(restroom).model_dump()
    base.update(
        inspection_count=inspection_count,
        latest_inspection_time=latest.inspect_time if latest else None,
        latest_inspection_score=latest.score if latest else None,
        avg_score=round(float(avg_score), 1) if avg_score is not None else None,
        open_issue_count=open_issue_count,
        total_issue_count=total_issue_count,
        env_record_count=env_record_count,
        env_score=latest_env.score if latest_env else None,
        env_grade=latest_env.grade if latest_env else None,
        env_record_time=latest_env.record_time if latest_env else None,
        env_regressed=bool(latest_env.regressed) if latest_env else False,
        env_regress_reason=latest_env.regress_reason if latest_env else None,
    )
    return RestroomDetail(**base)


def touch(db: Session, restroom_id: int) -> None:
    """巡查或问题变更后刷新台账更新时间。"""
    restroom = db.get(Restroom, restroom_id)
    if restroom is not None:
        restroom.updated_at = datetime.now()
        db.commit()
