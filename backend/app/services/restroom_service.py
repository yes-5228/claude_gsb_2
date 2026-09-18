"""公厕台账业务逻辑。"""

from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.constants import OPEN_ISSUE_STATUSES
from app.core.exceptions import ConflictError, DomainError, NotFoundError
from app.models import Inspection, Issue, Restroom
from app.schemas.restroom import RestroomCreate, RestroomDetail, RestroomOut, RestroomUpdate
from app.services import environment

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

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    column = SORTABLE_FIELDS.get(sort_by, Restroom.created_at)
    stmt = stmt.order_by(column.desc() if order == "desc" else column.asc(), Restroom.id.desc())
    rows = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)))
    return rows, total


def list_districts(db: Session) -> list[str]:
    return list(db.scalars(select(Restroom.district).distinct().order_by(Restroom.district)))


def enrich_env_summary(db: Session, rows: list[Restroom]) -> list[RestroomOut]:
    """台账列表批量附带最近环境卫生评价与退步标记。"""
    outs = [RestroomOut.model_validate(row) for row in rows]
    if not outs:
        return outs
    restroom_ids = [row.id for row in rows]
    # 取每个公厕最近两条带环境记录的巡查，比较得出最新一条是否相对退步
    records = list(
        db.scalars(
            select(Inspection)
            .where(Inspection.restroom_id.in_(restroom_ids), Inspection.env_score.is_not(None))
            .order_by(Inspection.inspect_time.desc(), Inspection.id.desc())
        )
    )
    grouped: dict[int, list[Inspection]] = {}
    for record in records:
        grouped.setdefault(record.restroom_id, []).append(record)

    out_by_id = {item.id: item for item in outs}
    for restroom_id, pair in grouped.items():
        latest = pair[0]
        previous = pair[1] if len(pair) > 1 else None
        out = out_by_id[restroom_id]
        out.latest_env_score = latest.env_score
        out.latest_env_grade = latest.env_grade
        out.latest_env_time = latest.inspect_time
        if previous is not None:
            out.env_regressed = environment.is_regression(
                latest.env_score, latest.env_grade, previous.env_score, previous.env_grade
            )
    return outs


def _count_env_regressions(db: Session, restroom_id: int) -> int:
    """统计某公厕按时间相邻的环境记录中出现明显退步的次数。"""
    records = list(
        db.scalars(
            select(Inspection)
            .where(Inspection.restroom_id == restroom_id, Inspection.env_score.is_not(None))
            .order_by(Inspection.inspect_time.asc(), Inspection.id.asc())
        )
    )
    count = 0
    for previous, current in zip(records, records[1:]):
        if environment.is_regression(
            current.env_score, current.env_grade, previous.env_score, previous.env_grade
        ):
            count += 1
    return count


def count_restrooms_with_env_regression(db: Session) -> int:
    """当前最新一条环境记录相对上一次明显退步的公厕数量（看板预警用）。"""
    records = list(
        db.scalars(
            select(Inspection)
            .where(Inspection.env_score.is_not(None))
            .order_by(Inspection.restroom_id, Inspection.inspect_time.asc(), Inspection.id.asc())
        )
    )
    latest: dict[int, Inspection] = {}
    previous: dict[int, Inspection] = {}
    for record in records:
        previous[record.restroom_id] = latest.get(record.restroom_id)
        latest[record.restroom_id] = record
    count = 0
    for restroom_id, current in latest.items():
        prev = previous.get(restroom_id)
        if prev is not None and environment.is_regression(
            current.env_score, current.env_grade, prev.env_score, prev.env_grade
        ):
            count += 1
    return count


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
    if (inspection_count or issue_count) and not force:
        raise ConflictError(
            f"该公厕已有 {inspection_count} 条巡查记录、{issue_count} 条问题记录，"
            "确需删除请使用 force=true"
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
    latest_env = db.scalars(
        select(Inspection)
        .where(Inspection.restroom_id == restroom_id, Inspection.env_score.is_not(None))
        .order_by(Inspection.inspect_time.desc(), Inspection.id.desc())
        .limit(2)
    ).all()
    latest_env_inspection = latest_env[0] if latest_env else None
    prev_env_inspection = latest_env[1] if len(latest_env) > 1 else None

    env_regressed = False
    if latest_env_inspection is not None and prev_env_inspection is not None:
        env_regressed = environment.is_regression(
            latest_env_inspection.env_score,
            latest_env_inspection.env_grade,
            prev_env_inspection.env_score,
            prev_env_inspection.env_grade,
        )

    base = RestroomOut.model_validate(restroom).model_dump()
    # 以下环境卫生汇总字段在下方单独计算，先剔除默认值避免重复传参
    for key in ("latest_env_score", "latest_env_grade", "latest_env_time", "env_regressed"):
        base.pop(key, None)
    return RestroomDetail(
        **base,
        inspection_count=inspection_count,
        latest_inspection_time=latest.inspect_time if latest else None,
        latest_inspection_score=latest.score if latest else None,
        avg_score=round(float(avg_score), 1) if avg_score is not None else None,
        open_issue_count=open_issue_count,
        total_issue_count=total_issue_count,
        latest_env_score=latest_env_inspection.env_score if latest_env_inspection else None,
        latest_env_grade=latest_env_inspection.env_grade if latest_env_inspection else None,
        latest_env_time=latest_env_inspection.inspect_time if latest_env_inspection else None,
        env_regressed=env_regressed,
        prev_env_score=prev_env_inspection.env_score if prev_env_inspection else None,
        prev_env_grade=prev_env_inspection.env_grade if prev_env_inspection else None,
        prev_env_time=prev_env_inspection.inspect_time if prev_env_inspection else None,
        env_regression_count=_count_env_regressions(db, restroom_id),
    )


def touch(db: Session, restroom_id: int) -> None:
    """巡查或问题变更后刷新台账更新时间。"""
    restroom = db.get(Restroom, restroom_id)
    if restroom is not None:
        restroom.updated_at = datetime.now()
        db.commit()
