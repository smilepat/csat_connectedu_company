# app/middleware/request_context.py
import time
import uuid
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# 수신은 두 가지 표기 모두 허용, 송신은 하이픈 소문자 i 로 통일
HDR_IN_LOWER = "x-request-id"
HDR_OUT = "X-Request-Id"  # 응답에 노출할 공식 표기

def _get_req_id_from_headers(request: Request) -> Optional[str]:
    # Starlette 헤더 dict는 case-insensitive
    h = request.headers
    return h.get(HDR_OUT) or h.get("X-Request-ID") or h.get(HDR_IN_LOWER)

class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()

        trace_id = _get_req_id_from_headers(request) or str(uuid.uuid4())

        # 다른 레이어와 호환: req_id/trace_id/idempotency_key 모두 세팅
        request.state.trace_id = trace_id
        request.state.req_id = trace_id
        request.state.idempotency_key = trace_id  # 업스트림이 멱등키 지원시 활용

        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            request.state.elapsed_ms = elapsed_ms

            if response is None:
                response = Response(status_code=500)

            # 응답 헤더에 trace id 삽입(표준화된 키로 1개만)
            response.headers[HDR_OUT] = trace_id

            # 브라우저에서 읽을 수 있도록 노출 (기존 값과 병합)
            expose = response.headers.get("Access-Control-Expose-Headers")
            if expose:
                # 이미 있으면 중복 없이 추가
                items = {h.strip() for h in expose.split(",")}
                items.add(HDR_OUT)
                response.headers["Access-Control-Expose-Headers"] = ", ".join(sorted(items))
            else:
                response.headers["Access-Control-Expose-Headers"] = HDR_OUT

            # 라우트/지연 시간의 실제 로깅은 main.py/로거에서 처리 (여기선 상태만 준비)
