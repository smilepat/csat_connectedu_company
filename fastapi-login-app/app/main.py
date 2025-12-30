# app/main.py
import os  # ✅ 추가: APP_DEBUG 읽기용
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, FileResponse, HTMLResponse
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import logging
import time
import uuid
import traceback  # ✅ 추가: 스택트레이스 문자열화

# ✅ 추가: 전역 예외 타입
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.settings import settings
from app.core.logging import configure_logging
from app.middleware.request_context import RequestContextMiddleware

# 라우터들 ...
from app.auth import router as auth_router
from app.routes.items import router as item_router
from app.routes.generate import router as generator_router
from app.routes.items_meta import router as item_meta_router
#from app.routes.image_gen import router as image_router
from app.routes.generate_multi import router as gen_router
from app.routes.suggest_types import router as suggest_router
from app.routes.generate_one import router as generate_one_router
from app.routes.pages import router as pages_router
from app.routes.export_docx import router as export_legacy_router, export_router

# ---------- 앱 초기화 ----------
configure_logging(settings.LOG_LEVEL)

DEBUG = os.getenv("APP_DEBUG", "0") == "1"  # ✅ 이미 있던 코드 유지

app = FastAPI(title=settings.SERVICE_NAME or "FastAPI 로그인 연동 예제")

# ---------- 미들웨어 ----------
app.add_middleware(RequestContextMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)

access_logger = logging.getLogger("access")

@app.middleware("http")
async def access_log_middleware(request: Request, call_next):
    start = time.perf_counter()
    trace_id = getattr(request.state, "trace_id", None)
    if not trace_id:
        trace_id = str(uuid.uuid4())
        request.state.trace_id = trace_id

    # ✅ 디버그 모드 표시 헤더
    request.state.debug = DEBUG

    response: Response | None = None
    try:
        response = await call_next(request)
        response.headers["X-Request-Id"] = trace_id
        if DEBUG:
            response.headers["X-Debug-Mode"] = "1"  # ✅ 확인용
        return response
    except Exception as e:
        # ✅ 전체 스택 로그 남기기(서버 로그)
        access_logger.exception(
            "unhandled_error",
            extra={"trace_id": trace_id, "method": request.method, "path": request.url.path},
        )
        # ✅ 디버그면 예외 메시지를 바로 보여줌
        if DEBUG:
            return JSONResponse(
                status_code=500,
                content={
                    "detail": f"[DEBUG] {e.__class__.__name__}: {e}",
                    "trace_id": trace_id,
                },
            )
        # 평소엔 기본 핸들러로
        raise
    finally:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        access_logger.info(
            "request_done",
            extra={
                "trace_id": trace_id,
                "method": request.method,
                "path": request.url.path,
                "status": getattr(response, "status_code", None),
                "latency_ms": elapsed_ms,
            },
        )

# ---------- ✅ 전역 예외 핸들러 (디버그일 때만 예외 메시지 노출) ----------
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    trace_id = getattr(request.state, "trace_id", None) or str(uuid.uuid4())
    if DEBUG:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": f"[DEBUG] {exc.detail}", "trace_id": trace_id},
        )
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc.detail)})

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    trace_id = getattr(request.state, "trace_id", None) or str(uuid.uuid4())
    # 서버 로그에 스택트레이스
    logging.getLogger("uvicorn.error").error(
        "UNHANDLED %s: %s\n%s", type(exc).__name__, exc, traceback.format_exc()
    )
    if DEBUG:
        return JSONResponse(
            status_code=500,
            content={"detail": f"[DEBUG] {exc.__class__.__name__}: {exc}", "trace_id": trace_id},
        )
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

# ---------- 라우터 등록 ----------
app.include_router(auth_router, prefix="/api/auth")
app.include_router(item_router, prefix="/items")
app.include_router(generator_router, prefix="/api/generate")
app.include_router(item_meta_router)
#app.include_router(image_router)
app.include_router(gen_router)
app.include_router(suggest_router)
app.include_router(generate_one_router, prefix="/api")
app.include_router(export_legacy_router)  # /api/pages/export_docx
app.include_router(export_router)         # /api/exports/docx
app.include_router(pages_router)

# ---------- OpenAPI ----------
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version="1.0.0",
        description="로그인 후 토큰으로 인증하는 FastAPI 예제",
        routes=app.routes,
    )
    openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})
    openapi_schema["components"]["securitySchemes"]["bearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "UUID",
    }
    for path in openapi_schema.get("paths", {}):
        for method in openapi_schema["paths"][path]:
            openapi_schema["paths"][path][method]["security"] = [{"bearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# ---------- 헬스 체크 ----------
@app.get("/api/health")
def health_check():
    return {"message": "OK"}

# ---------- 프론트엔드 정적 파일 서빙 ----------
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"

# 정적 파일 마운트 (CSS, JS 등)
if (BASE_DIR / "static").exists():
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# 메인 페이지 (로그인)
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = TEMPLATES_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("<h1>ConnectedU ItemGen API</h1><p><a href='/docs'>API 문서</a></p>")

# 대시보드 페이지
@app.get("/dashboard.html", response_class=HTMLResponse)
async def serve_dashboard():
    dashboard_file = TEMPLATES_DIR / "dashboard.html"
    if dashboard_file.exists():
        return FileResponse(dashboard_file)
    return HTMLResponse("<h1>Dashboard not found</h1>")

# 문항 생성 페이지
@app.get("/generate.html", response_class=HTMLResponse)
async def serve_generate():
    generate_file = TEMPLATES_DIR / "generate.html"
    if generate_file.exists():
        return FileResponse(generate_file)
    return HTMLResponse("<h1>Generate page not found</h1>")
