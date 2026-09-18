"""公厕台账接口。"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import PaginationDep, build_meta
from app.core.database import get_db
from app.schemas.common import MessageOut, Page
from app.schemas.restroom import RestroomCreate, RestroomDetail, RestroomOut, RestroomUpdate
from app.services import environment_service, restroom_service

router = APIRouter(prefix="/restrooms", tags=["公厕台账"])


@router.get("/meta/districts", response_model=list[str], summary="区域列表")
def list_districts(db: Annotated[Session, Depends(get_db)]) -> list[str]:
    return restroom_service.list_districts(db)


@router.get("", response_model=Page[RestroomOut], summary="公厕列表")
def list_restrooms(
    db: Annotated[Session, Depends(get_db)],
    pagination: PaginationDep,
    keyword: Annotated[str | None, Query(description="名称/编号/地址/责任人模糊搜索")] = None,
    district: Annotated[str | None, Query(description="所属区域")] = None,
    status: Annotated[str | None, Query(description="开放状态")] = None,
    grade: Annotated[str | None, Query(description="公厕等级")] = None,
    env_regressed: Annotated[bool | None, Query(description="仅看环境卫生明显退步")] = None,
    sort_by: Annotated[str, Query(description="排序字段")] = "created_at",
    order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
) -> Page[RestroomOut]:
    rows, total = restroom_service.list_restrooms(
        db,
        keyword=keyword,
        district=district,
        status=status,
        grade=grade,
        env_regressed=env_regressed,
        page=pagination.page,
        page_size=pagination.page_size,
        sort_by=sort_by,
        order=order,
    )
    # 台账列表附带每座公厕最新一条环境卫生评价，明显退步的在台账中标记
    latest_env = environment_service.latest_by_restrooms(db, [row.id for row in rows])
    items = []
    for row in rows:
        item = RestroomOut.model_validate(row)
        env = latest_env.get(row.id)
        if env is not None:
            item.env_score = env.score
            item.env_grade = env.grade
            item.env_record_time = env.record_time
            item.env_regressed = bool(env.regressed)
        items.append(item)
    return Page[RestroomOut](items=items, meta=build_meta(total, pagination))


@router.post("", response_model=RestroomOut, status_code=201, summary="新增公厕")
def create_restroom(
    payload: RestroomCreate, db: Annotated[Session, Depends(get_db)]
) -> RestroomOut:
    return RestroomOut.model_validate(restroom_service.create_restroom(db, payload))


@router.get("/{restroom_id}", response_model=RestroomDetail, summary="公厕详情")
def get_restroom(restroom_id: int, db: Annotated[Session, Depends(get_db)]) -> RestroomDetail:
    return restroom_service.get_restroom_detail(db, restroom_id)


@router.patch("/{restroom_id}", response_model=RestroomOut, summary="更新公厕")
def update_restroom(
    restroom_id: int, payload: RestroomUpdate, db: Annotated[Session, Depends(get_db)]
) -> RestroomOut:
    return RestroomOut.model_validate(restroom_service.update_restroom(db, restroom_id, payload))


@router.delete("/{restroom_id}", response_model=MessageOut, summary="删除公厕")
def delete_restroom(
    restroom_id: int,
    db: Annotated[Session, Depends(get_db)],
    force: Annotated[bool, Query(description="为 true 时级联删除巡查与问题记录")] = False,
) -> MessageOut:
    restroom_service.delete_restroom(db, restroom_id, force=force)
    return MessageOut(message="删除成功")
