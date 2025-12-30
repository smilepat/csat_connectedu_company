# app/routes/pages.py
from fastapi import APIRouter, Request, HTTPException, Header, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
import os, requests, json

import redis


router = APIRouter(prefix="/api/pages", tags=["pages"])

# =========================
# Java Pages API Endpoints
# =========================
#JAVA_BASE = "http://14.41.57.208:22381/api/pages"
JAVA_BASE = "https://api-chungbuk.connectenglish.kr:8442/api/pages"
JAVA_ADD_URL       = f"{JAVA_BASE}/add"                # 페이지 생성
JAVA_EDIT_URL      = f"{JAVA_BASE}/edit"               # 페이지 수정
JAVA_DELETE_URL    = f"{JAVA_BASE}/delete"             # 페이지 삭제
JAVA_LIST_URL      = f"{JAVA_BASE}/list"               # 페이지 리스트
JAVA_DETAIL_URL    = f"{JAVA_BASE}/detail"             # 페이지 디테일
JAVA_Q_ADD_URL     = f"{JAVA_BASE}/question/add"       # 페이지 문항 추가
JAVA_Q_EDIT_URL    = f"{JAVA_BASE}/question/edit"      # 페이지 문항 수정

# Basic Auth 헤더 (운영에서는 환경변수로 주입 권장)
# 예시 문서: Authorization: Basic Y2h1bmdidWs6OW... :contentReference[oaicite:5]{index=5}
JAVA_BASIC_AUTH = os.getenv("JAVA_PAGES_BASIC_AUTH", "Basic Y2h1bmdidWs6OWUzZDViNmM4YTJmNGM3ZDFiM2U3ZjEyYTZkOWUwYjQ=")

# =========================
# Redis & Token
# =========================
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def token_required(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="인증 토큰이 필요합니다")
    token = authorization.replace("Bearer ", "")
    user_data = r.get(f"auth:{token}")
    if not user_data:
        raise HTTPException(status_code=401, detail="토큰이 만료되었거나 유효하지 않습니다")
    return json.loads(user_data)

# =========================
# Pydantic Schemas
# =========================
class PageAddRequest(BaseModel):
    title: str
    description: str
    is_public: bool
    cover_image: Optional[str] = None

class PageEditRequest(BaseModel):
    page_id: int
    title: str
    description: str
    status: str = Field(pattern="^(draft|published|archived)$")
    is_public: bool
    cover_image: Optional[str] = None

class PageDeleteRequest(BaseModel):
    page_id: int

class PageListRequest(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1)
    sch_status: str = Field("all", pattern="^(all|draft|published|archived)$")

class PageDetailRequest(BaseModel):
    page_id: int

class QuestionEntry(BaseModel):
    question_seq: int
    display_order: int
    section_label: str
    points: int
    note: Optional[str] = None

class PageQuestionsRequest(BaseModel):
    page_id: int
    questions: List[QuestionEntry] = Field(default_factory=list)

# =========================
# Helpers
# =========================
def _java_headers():
    return {
        "Authorization": JAVA_BASIC_AUTH,  # Basic ...
        "Content-Type": "application/json",
    }

def _post_java(url: str, payload: dict):
    # 운영 환경 인증서 이슈가 있으면 verify=False 유지
    return requests.post(url, json=payload, headers=_java_headers(), timeout=8, verify=False)

def _safe_json(resp: requests.Response) -> Optional[dict]:
    try:
        return resp.json()
    except ValueError:
        return None

def _pick_id(d: dict) -> Optional[int]:
    """여러 응답 쉐이프에서 page_id를 탐색해 정수로 반환"""
    paths = [
        ["page_id"], ["pageId"], ["page_seq"],
        ["data", "page_id"], ["data", "pageId"], ["data", "page_seq"],
        ["page", "page_id"], ["page", "pageId"], ["page", "page_seq"],
        ["data", "page", "page_id"], ["data", "page", "pageId"], ["data", "page", "page_seq"],
    ]
    for path in paths:
        cur: Any = d
        ok = True
        for k in path:
            if isinstance(cur, dict) and k in cur:
                cur = cur[k]
            else:
                ok = False
                break
        if ok and cur is not None:
            try:
                return int(cur)
            except (TypeError, ValueError):
                pass
    return None

def _ok_or_500(resp: requests.Response, where: str) -> dict:
    j = _safe_json(resp)
    if resp.status_code != 200 or not isinstance(j, dict):
        raise HTTPException(status_code=500, detail=f"Java API 에러({where})")
    return j

# =========================
# Endpoints
# =========================

@router.post("/add")
def pages_add(body: PageAddRequest, user=Depends(token_required)):
    """
    페이지 생성
    필수: user_seq, title, description, is_public (cover_image 선택)
    """
    payload = {
        "user_seq": user["user_seq"],
        "title": body.title,
        "description": body.description,
        "cover_image": body.cover_image or "",
        "is_public": str(body.is_public).lower(),  # true/false 문자열로 전달
    }
    try:
        print("📤 /pages/add payload\n", json.dumps(payload, ensure_ascii=False, indent=2))
        resp = _post_java(JAVA_ADD_URL, payload)
        j = _ok_or_500(resp, "pages/add")

        # ✅ 표준화: 항상 page_id를 루트에 실어서 반환
        page_id = _pick_id(j)
        return {
            "result": "0",
            "page_id": page_id,
            "data": j,  # 원본 응답도 보관
        }
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Java API 요청 실패: {e}")

@router.post("/edit")
def pages_edit(body: PageEditRequest, user=Depends(token_required)):
    """
    페이지 수정
    필수: page_id, user_seq, title, description, status(draft|published|archived), is_public
    """
    payload = {
        "page_id": body.page_id,
        "user_seq": user["user_seq"],
        "title": body.title,
        "description": body.description,
        "cover_image": body.cover_image or "",
        "status": body.status,
        "is_public": str(body.is_public).lower(),
    }
    try:
        print("📤 /pages/edit payload\n", json.dumps(payload, ensure_ascii=False, indent=2))
        resp = _post_java(JAVA_EDIT_URL, payload)
        j = _ok_or_500(resp, "pages/edit")
        return {"result": "0", "data": j}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Java API 요청 실패: {e}")

@router.post("/delete")
def pages_delete(body: PageDeleteRequest, user=Depends(token_required)):
    """
    페이지 삭제
    필수: page_id, user_seq
    """
    payload = {
        "page_id": body.page_id,
        "user_seq": user["user_seq"],
    }
    try:
        print("📤 /pages/delete payload\n", json.dumps(payload, ensure_ascii=False, indent=2))
        resp = _post_java(JAVA_DELETE_URL, payload)
        j = _ok_or_500(resp, "pages/delete")
        return {"result": "0", "data": j}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Java API 요청 실패: {e}")

@router.post("/list")
def pages_list(body: PageListRequest, user=Depends(token_required)):
    """
    페이지 리스트
    필수: page, page_size, sch_user_seq, sch_status
    """
    payload = {
        "page": body.page,
        "page_size": body.page_size,
        "sch_user_seq": user["user_seq"],
        "sch_status": body.sch_status,
    }
    try:
        print("📤 /pages/list payload\n", json.dumps(payload, ensure_ascii=False, indent=2))
        resp = _post_java(JAVA_LIST_URL, payload)
        j = _ok_or_500(resp, "pages/list")
        return {"result": "0", "data": j}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Java API 요청 실패: {e}")

@router.post("/detail")
def pages_detail(body: PageDetailRequest, user=Depends(token_required)):
    """
    페이지 디테일
    필수: page_id, user_seq
    응답: data.page + data.questions 구조(문서 예시 참조)
    """
    payload = {
        "page_id": body.page_id,
        "user_seq": user["user_seq"],
    }
    try:
        print("📤 /pages/detail payload\n", json.dumps(payload, ensure_ascii=False, indent=2))
        resp = _post_java(JAVA_DETAIL_URL, payload)
        j = _ok_or_500(resp, "pages/detail")
        return {"result": "0", "data": j}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Java API 요청 실패: {e}")

@router.post("/question/add")
def pages_question_add(body: PageQuestionsRequest, user=Depends(token_required)):
    """
    페이지 문항 추가
    필수: page_id, user_seq, questions[ {question_seq, display_order, section_label, points, note?} ]
    """
    payload = {
        "page_id": body.page_id,
        "user_seq": user["user_seq"],
        "questions": [q.model_dump() for q in body.questions],
    }
    try:
        print("📤 /pages/question/add payload\n", json.dumps(payload, ensure_ascii=False, indent=2))
        resp = _post_java(JAVA_Q_ADD_URL, payload)
        j = _ok_or_500(resp, "pages/question/add")
        return {"result": "0", "data": j}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Java API 요청 실패: {e}")

@router.post("/question/edit")
def pages_question_edit(body: PageQuestionsRequest, user=Depends(token_required)):
    """
    페이지 문항 수정
    필수: page_id, user_seq, questions[ {question_seq, display_order, section_label, points, note?} ]
    """
    payload = {
        "page_id": body.page_id,
        "user_seq": user["user_seq"],
        "questions": [q.model_dump() for q in body.questions],
    }
    try:
        print("📤 /pages/question/edit payload\n", json.dumps(payload, ensure_ascii=False, indent=2))
        resp = _post_java(JAVA_Q_EDIT_URL, payload)
        j = _ok_or_500(resp, "pages/question/edit")
        return {"result": "0", "data": j}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Java API 요청 실패: {e}")