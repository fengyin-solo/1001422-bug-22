"""竣工验收业务规则：状态流转、字段校验与筛选口径都收在这里。"""
from __future__ import annotations

import math
from typing import Any

from app.store import store

MODULE = "accept"
REQUIRED_FIELDS = ["验收单号", "关联施工", "验收项目"]
STATUS_ORDER = ["待验收", "验收中", "已通过", "需返工"]
ACTION_RULES = {"开始验收": "验收中", "确认通过": "已通过", "下发返工": "需返工"}
NEGATIVE_ACTIONS = []

# abnormal 标记的单据视为已作废：列表、筛选与统计都按这个口径走，不再混入正常状态。
VOID_STATUS = "已作废"
DISPLAY_STATUSES = [*STATUS_ORDER, VOID_STATUS]
DEFAULT_SIZE = 20


class AcceptService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> dict[str, Any]:
        rows = [self._serialize(row) for row in self._filtered_rows(keyword=keyword, status=status)]
        total = len(rows)
        size, size_notice = self._checked_size(size)
        pages = max(1, math.ceil(total / size))
        page, page_notice = self._checked_page(page, pages)
        start = (page - 1) * size
        notices = [notice for notice in (size_notice, page_notice) if notice]
        return {
            "items": rows[start:start + size],
            "total": total,
            "page": page,
            "size": size,
            "pages": pages,
            "notice": "；".join(notices) if notices else None,
            "stats": self._status_counts(rows),
        }

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        row = store.find(MODULE, entry_id)
        return self._serialize(row) if row is not None else None

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS})
        entry["status"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return entry, []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"验收单 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于竣工验收可执行范围"
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return entry, f"验收单已{action}"

    def _filtered_rows(self, *, keyword: str | None, status: str | None) -> list[dict[str, Any]]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("验收单号", ""))]
        if status:
            rows = [row for row in rows if self._display_status(row) == status]
        return rows

    @staticmethod
    def _display_status(row: dict[str, Any]) -> str:
        """单据对外展示的状态：作废单据一律显示已作废，不再残留原状态。"""
        if row.get("abnormal"):
            return VOID_STATUS
        return str(row.get("status") or STATUS_ORDER[0])

    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        item = dict(row)
        item["验收状态"] = self._display_status(row)
        return item

    @staticmethod
    def _status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
        """统计与列表同一份过滤结果，卡片、表格、页脚才能对上。"""
        counts = {status: 0 for status in DISPLAY_STATUSES}
        for row in rows:
            key = str(row["验收状态"])
            counts[key] = counts.get(key, 0) + 1
        return counts

    @staticmethod
    def _checked_size(size: int) -> tuple[int, str | None]:
        if size < 1:
            return DEFAULT_SIZE, f"每页条数 {size} 不合法：最小为 1 条，已按每页 {DEFAULT_SIZE} 条显示"
        return size, None

    @staticmethod
    def _checked_page(page: int, pages: int) -> tuple[int, str | None]:
        """页码先校验再落页：小了回第一页，大了落最后一页，并讲清是哪一头越界。"""
        if page < 1:
            return 1, f"页码 {page} 不合法：最小为第 1 页，已回到第 1 页"
        if page > pages:
            return pages, f"页码 {page} 超出上限：当前共 {pages} 页，已落到最后一页（第 {pages} 页）"
        return page, None
