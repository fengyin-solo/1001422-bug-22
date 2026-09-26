"""竣工验收业务规则：状态流转、字段校验与筛选口径都收在这里。"""
from __future__ import annotations

from typing import Any

from app.store import store

MODULE = "accept"
REQUIRED_FIELDS = ["验收单号", "关联施工", "验收项目"]
STATUS_ORDER = ["待验收", "验收中", "已通过", "需返工", "已作废"]
ACTION_RULES = {"开始验收": "验收中", "确认通过": "已通过", "下发返工": "需返工", "作废验收": "已作废"}
NEGATIVE_ACTIONS = ["作废验收"]
VOID_STATUS = "已作废"


class AcceptService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int, int, str | None]:
        # 作废的验收单不再留在列表里，避免翻页时反复出现、总数也对不上
        rows = [row for row in store.rows(MODULE) if row.get("status") != VOID_STATUS]
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("验收单号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        total = len(rows)
        page, notice = self._clamp_page(page, size, total)
        start = (page - 1) * size
        return rows[start:start + size], total, page, notice

    @staticmethod
    def _clamp_page(page: int, size: int, total: int) -> tuple[int, str | None]:
        """页码先校验再落页：越过哪一头就在提示里讲清哪一头不合法。"""
        if page < 1:
            return 1, f"页码 {page} 不合法：小于第 1 页，已回到第 1 页"
        max_page = max((total + size - 1) // size, 1)
        if page > max_page:
            return max_page, f"页码 {page} 不合法：超出最后一页，共 {max_page} 页，已落到第 {max_page} 页"
        return page, None

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

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
