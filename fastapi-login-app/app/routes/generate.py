# app/routes/generate.py
from fastapi import APIRouter, HTTPException, Body, Request
from fastapi.responses import JSONResponse, StreamingResponse
import logging
import asyncio
import json
import time

from app.schemas.generate import GenerateRequest
from app.services.item_generator import generate_item

router = APIRouter()
log = logging.getLogger("app.generate")

HEARTBEAT_INTERVAL_SEC = 8  # 하트비트 주기(5~15초 권장)

def _dump_model(m):
    # pydantic v2 / v1 호환
    for attr in ("model_dump", "dict"):
        fn = getattr(m, attr, None)
        if callable(fn):
            try:
                return fn(exclude_unset=True)
            except TypeError:
                return fn()
    return dict(m or {})

async def _stream_item_make_json(item_id: str, payload: dict, trace_id: str | None):
    """
    스트리밍 제너레이터:
    - 응답을 바로 시작해 클라이언트 쪽 타임아웃 방지
    - HEARTBEAT_INTERVAL_SEC마다 하트비트 바이트를 전송
    - 작업 종료 시 최종 결과 JSON을 붙이고 닫기
    """
    # 응답 시작(브라우저/프록시에 '본문이 시작됐다'고 알림)
    preamble = {
        "itemId": item_id,
        "status": "stream",
        "trace_id": trace_id,
        "ts": int(time.time() * 1000),
    }
    yield (json.dumps(preamble, ensure_ascii=False) + "\n").encode("utf-8")

    # 실제 작업 비동기 수행
    task = asyncio.create_task(generate_item(item_id=item_id, payload=payload, trace_id=trace_id))

    try:
        # 작업 진행 중 하트비트
        while not task.done():
            await asyncio.sleep(HEARTBEAT_INTERVAL_SEC)
            hb = {"heartbeat": int(time.time() * 1000)}
            # NDJSON 스타일 라인 단위 전송(각 라인은 독립 JSON)
            yield (json.dumps(hb, ensure_ascii=False) + "\n").encode("utf-8")

        # 최종 결과
        result = await task
        final = {
            "itemId": item_id,
            "status": "ok" if result.get("ok") else "error",
            "data": result,
            "trace_id": trace_id,
        }
        yield (json.dumps(final, ensure_ascii=False) + "\n").encode("utf-8")

    except Exception as e:
        # 스트리밍 중 오류도 JSON 라인으로 마무리
        err = {
            "itemId": item_id,
            "status": "error",
            "data": {
                "ok": False,
                "error": {"type": "RouteStreamError", "message": str(e)},
                "meta": {"trace_id": trace_id},
            },
            "trace_id": trace_id,
        }
        yield (json.dumps(err, ensure_ascii=False) + "\n").encode("utf-8")

@router.post("/{item_id}", response_model=None)
async def generate_cs_item(
    item_id: str,
    request: Request,
    req: GenerateRequest = Body(...),
):
    trace_id = getattr(request.state, "trace_id", None)
    log.info("route_generate_start", extra={"trace_id": trace_id, "item_id": item_id})

    # 쿼리로 스트리밍 모드 제어 (?stream=1 / true / yes)
    qp = request.query_params
    stream_flag = (qp.get("stream", "").lower() in {"1", "true", "yes", "sse"})

    try:
        body = _dump_model(req)  # {"difficulty": ..., "topic": ..., "itemId": ...} 등
        body_item_id = (str(body.get("itemId") or body.get("item_id") or "")).strip()
        if body_item_id and body_item_id != item_id:
            log.warning(
                "item_id_mismatch",
                extra={"trace_id": trace_id, "path": item_id, "body": body_item_id},
            )

        # 스트리밍 모드: NDJSON으로 라인 단위 이벤트 전송
        if stream_flag:
            return StreamingResponse(
                _stream_item_make_json(item_id=item_id, payload=body, trace_id=trace_id),
                media_type="application/x-ndjson; charset=utf-8",
                headers={"X-Request-Id": trace_id} if trace_id else None,
            )

        # 비스트리밍(기존 동작)
        result = await generate_item(item_id=item_id, payload=body, trace_id=trace_id)

        status_code = 200 if result.get("ok") else 422
        body_status = "ok" if result.get("ok") else "error"

        return JSONResponse(
            status_code=status_code,
            content={"itemId": item_id, "status": body_status, "data": result},
            headers={"X-Request-Id": trace_id} if trace_id else None,
        )

    except ValueError as e:
        log.warning(
            "route_generate_value_error",
            extra={"trace_id": trace_id, "item_id": item_id, "detail": str(e)},
        )
        return JSONResponse(
            status_code=404,
            content={"code": "NOT_FOUND", "message": str(e), "trace_id": trace_id},
            headers={"X-Request-Id": trace_id} if trace_id else None,
        )

    except HTTPException as e:
        msg = e.detail if isinstance(e.detail, str) else str(e.detail)
        log.warning(
            "route_generate_http_error",
            extra={
                "trace_id": trace_id,
                "item_id": item_id,
                "status_code": e.status_code,
                "detail": msg,
            },
        )
        return JSONResponse(
            status_code=e.status_code,
            content={"code": "UPSTREAM_ERROR", "message": msg, "trace_id": trace_id},
            headers={"X-Request-Id": trace_id} if trace_id else None,
        )

    except Exception:
        log.exception(
            "route_generate_unexpected_error", extra={"trace_id": trace_id, "item_id": item_id}
        )
        return JSONResponse(
            status_code=500,
            content={"code": "INTERNAL_ERROR", "message": "문항 생성 실패", "trace_id": trace_id},
            headers={"X-Request-Id": trace_id} if trace_id else None,
        )
