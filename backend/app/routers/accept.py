"""竣工验收接口：维护验收单，覆盖开始验收、确认通过、下发返工等动作。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.accept import AcceptService

router = APIRouter(prefix="/api/accept", tags=["竣工验收"])

service = AcceptService()

LIST_FIELDS = ["验收单号", "关联施工", "验收项目", "验收标准", "验收结论", "验收人员", "验收日期", "验收状态"]
STATUSES = ["待验收", "验收中", "已通过", "需返工", "已作废"]


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按验收单号检索"),
    status: str | None = Query(default=None, description="待验收、验收中、已通过、需返工、已作废"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按验收单号与状态过滤竣工验收列表；没有数据时返回空页，不报错。

    页码越界时先校验再落页（小了回第一页、大了落最后一页），并通过 notice
    说明是哪一头不合法；total、pages 与 items 始终来自同一份过滤结果。
    """
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    result = service.list_entries(keyword=keyword, status=status, page=page, size=size)
    return PageResult(**result)


@router.get("/export")
def export_entries() -> dict[str, Any]:
    """导出竣工验收清单：返回当前过滤条件下的全量数据。

    声明在 `/{entry_id}` 之前，否则 "export" 会被当成验收单 id 抢走。
    """
    result = service.list_entries(page=1, size=10000)
    return {"module": "accept", "total": result["total"], "items": result["items"]}


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条验收单明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"验收单 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条验收单，缺字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="验收单已登记", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: dict[str, Any] = Body(default_factory=dict)) -> ActionResult:
    """对单条验收单执行开始验收、确认通过、下发返工；不允许的动作会被拦下并说明原因。

    动作名既认 `{ "values": { "action": ... } }`，也认前端平铺的 `{ "action": ... }`。
    """
    values = payload.get("values") if isinstance(payload.get("values"), dict) else payload
    action = str(values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
