"""环境卫生量化记录接口。"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import PaginationDep, build_meta
from app.core.database import get_db
from app.schemas.common import MessageOut, Page
from app.schemas.environment import (
    EnvironmentRecordCreate,
    EnvironmentRecordOut,
    EnvironmentRecordUpdate,
    EnvironmentTrend,
)
from app.services import environment_service

router = APIRouter(prefix="/environment-records", tags=["环境卫生"])


@router.get("/trend", response_model=EnvironmentTrend, summary="同一公厕环境卫生时间对比")
def get_trend(
    db: Annotated[Session, Depends(get_db)],
    restroom_id: Annotated[int, Query(description="公厕 id")],
) -> EnvironmentTrend:
    return environment_service.get_trend(db, restroom_id)


@router.get("", response_model=Page[EnvironmentRecordOut], summary="环境卫生记录列表")
def list_records(
    db: Annotated[Session, Depends(get_db)],
    pagination: PaginationDep,
    restroom_id: Annotated[int | None, Query(description="按公厕过滤")] = None,
    district: Annotated[str | None, Query(description="按区域过滤")] = None,
    recorder: Annotated[str | None, Query(description="记录人")] = None,
    grade: Annotated[str | None, Query(description="评价等级")] = None,
    regressed: Annotated[bool | None, Query(description="仅看明显退步")] = None,
    keyword: Annotated[str | None, Query(description="公厕名称/记录人/备注模糊搜索")] = None,
    date_from: Annotated[date | None, Query(description="开始日期")] = None,
    date_to: Annotated[date | None, Query(description="结束日期")] = None,
    sort_by: Annotated[str, Query(description="排序字段")] = "record_time",
    order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
) -> Page[EnvironmentRecordOut]:
    rows, total = environment_service.list_records(
        db,
        restroom_id=restroom_id,
        district=district,
        recorder=recorder,
        grade=grade,
        regressed=regressed,
        keyword=keyword,
        date_from=date_from,
        date_to=date_to,
        page=pagination.page,
        page_size=pagination.page_size,
        sort_by=sort_by,
        order=order,
    )
    return Page[EnvironmentRecordOut](
        items=[environment_service.to_out(row) for row in rows],
        meta=build_meta(total, pagination),
    )


@router.post("", response_model=EnvironmentRecordOut, status_code=201, summary="新增环境卫生记录")
def create_record(
    payload: EnvironmentRecordCreate, db: Annotated[Session, Depends(get_db)]
) -> EnvironmentRecordOut:
    return environment_service.to_out(environment_service.create_record(db, payload))


@router.get("/{record_id}", response_model=EnvironmentRecordOut, summary="环境卫生记录详情")
def get_record(record_id: int, db: Annotated[Session, Depends(get_db)]) -> EnvironmentRecordOut:
    return environment_service.to_out(environment_service.get_record(db, record_id))


@router.patch("/{record_id}", response_model=EnvironmentRecordOut, summary="更新环境卫生记录")
def update_record(
    record_id: int,
    payload: EnvironmentRecordUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> EnvironmentRecordOut:
    return environment_service.to_out(environment_service.update_record(db, record_id, payload))


@router.delete("/{record_id}", response_model=MessageOut, summary="删除环境卫生记录")
def delete_record(record_id: int, db: Annotated[Session, Depends(get_db)]) -> MessageOut:
    environment_service.delete_record(db, record_id)
    return MessageOut(message="删除成功")
