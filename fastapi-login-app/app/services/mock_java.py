# app/services/mock_java.py
import os, json, time
from typing import Dict, Any, List, Optional

USE_REDIS = True
try:
    import redis  # type: ignore
except Exception:
    USE_REDIS = False

# ---- 저장소 ----
class Store:
    def __init__(self):
        self.mem = {"autoinc": 1000, "pages": {}}  # page_id: page
        self.r = None
        if USE_REDIS:
            try:
                self.r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
                # test
                self.r.ping()
            except Exception:
                self.r = None

    def _load(self):
        if self.r:
            raw = self.r.get("mock:pages")
            auto = self.r.get("mock:autoinc")
            if raw:
                self.mem["pages"] = json.loads(raw)
            if auto:
                self.mem["autoinc"] = int(auto)

    def _save(self):
        if self.r:
            self.r.set("mock:pages", json.dumps(self.mem["pages"], ensure_ascii=False))
            self.r.set("mock:autoinc", str(self.mem["autoinc"]))

    def next_id(self) -> int:
        self._load()
        self.mem["autoinc"] += 1
        self._save()
        return self.mem["autoinc"]

    def create_page(self, user_seq: int, title: str, description: str = "") -> int:
        self._load()
        pid = self.next_id()
        now = int(time.time())
        self.mem["pages"][str(pid)] = {
            "page_id": pid,
            "user_seq": user_seq,
            "title": title,
            "description": description or "",
            "created_at": now,
            "updated_at": now,
            "items": [],  # [{question_seq, display_order, points, section_label, note}]
        }
        self._save()
        return pid

    def list_pages(self, user_seq: int) -> List[Dict[str, Any]]:
        self._load()
        pages = [
            p for p in self.mem["pages"].values()
            if int(p.get("user_seq", 0)) == int(user_seq)
        ]
        # 최신순
        pages.sort(key=lambda p: p.get("updated_at", 0), reverse=True)
        # 요약 형태
        return [
            {
                "page_id": p["page_id"],
                "title": p["title"],
                "description": p.get("description", ""),
                "created_at": p.get("created_at"),
                "updated_at": p.get("updated_at"),
                "total_items": len(p.get("items", [])),
            }
            for p in pages
        ]

    def get_page(self, page_id: int, user_seq: int) -> Optional[Dict[str, Any]]:
        self._load()
        p = self.mem["pages"].get(str(page_id))
        if not p or int(p.get("user_seq", 0)) != int(user_seq):
            return None
        return p

    def edit_page(self, page_id: int, user_seq: int, title: Optional[str], description: Optional[str]) -> bool:
        self._load()
        p = self.get_page(page_id, user_seq)
        if not p: return False
        if title is not None: p["title"] = title
        if description is not None: p["description"] = description
        p["updated_at"] = int(time.time())
        self._save()
        return True

    def delete_page(self, page_id: int, user_seq: int) -> bool:
        self._load()
        p = self.get_page(page_id, user_seq)
        if not p: return False
        self.mem["pages"].pop(str(page_id), None)
        self._save()
        return True

    def compose(self, page_id: int, user_seq: int, add: List[Dict[str, Any]], reorder: List[Dict[str, Any]], remove: List[int]) -> Dict[str, Any]:
        self._load()
        p = self.get_page(page_id, user_seq)
        if not p: return {"result": "9", "message": "PAGE_NOT_FOUND"}

        # 현재 items 맵
        items = {it["question_seq"]: it for it in p.get("items", [])}

        # remove
        for qid in remove or []:
            items.pop(qid, None)

        # add (upsert)
        for it in add or []:
            qid = int(it["question_seq"])
            items[qid] = {
                "question_seq": qid,
                "display_order": int(it.get("display_order", 9999)),
                "points": it.get("points"),
                "section_label": it.get("section_label"),
                "note": it.get("note"),
            }

        # reorder
        for it in reorder or []:
            qid = int(it["question_seq"])
            if qid in items:
                items[qid]["display_order"] = int(it.get("display_order", items[qid]["display_order"]))

        # 정렬 재적용
        ordered = sorted(items.values(), key=lambda x: x.get("display_order", 9999))
        for idx, it in enumerate(ordered, start=1):
            it["display_order"] = idx

        p["items"] = ordered
        p["updated_at"] = int(time.time())
        self._save()

        return {"result": "0", "data": {"page_id": page_id, "items": ordered}}

STORE = Store()

# ---- 라우팅 스위치 ----
async def mock_java(path: str, payload: Dict[str, Any]):
    """
    FastAPI 개발 중 자바 API 없이도 동일한 JSON 포맷을 반환하도록 하는 목 구현.
    path: "/pages/add" 등
    """
    user_seq = int(payload.get("user_seq", 0))

    if path == "/pages/add":
        title = payload.get("title") or "Untitled"
        description = payload.get("description") or ""
        pid = STORE.create_page(user_seq, title, description)
        return {"result": "0", "data": {"page_id": pid}}

    if path == "/pages/list":
        lst = STORE.list_pages(user_seq)
        return {"result": "0", "data": lst}

    if path == "/pages/detail":
        pid = int(payload.get("page_id", 0))
        p = STORE.get_page(pid, user_seq)
        if not p:
            return {"result": "9", "message": "PAGE_NOT_FOUND"}
        return {"result": "0", "data": p}

    if path == "/pages/edit":
        pid = int(payload.get("page_id", 0))
        ok = STORE.edit_page(pid, user_seq, payload.get("title"), payload.get("description"))
        if not ok:
            return {"result": "9", "message": "PAGE_NOT_FOUND"}
        p = STORE.get_page(pid, user_seq)
        return {"result": "0", "data": p}

    if path == "/pages/delete":
        pid = int(payload.get("page_id", 0))
        ok = STORE.delete_page(pid, user_seq)
        if not ok:
            return {"result": "9", "message": "PAGE_NOT_FOUND"}
        return {"result": "0", "data": {"deleted": True, "page_id": pid}}

    if path == "/pages/compose":
        pid = int(payload.get("page_id", 0))
        add = payload.get("add") or []
        reorder = payload.get("reorder") or []
        remove = payload.get("remove") or []
        return STORE.compose(pid, user_seq, add, reorder, remove)

    # 정의 안 된 엔드포인트
    return {"result": "9", "message": f"MOCK_NOT_IMPLEMENTED: {path}"}
