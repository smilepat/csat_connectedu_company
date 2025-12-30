# app/routes/export_docx.py
from fastapi import APIRouter, Request, Depends, HTTPException
from starlette.background import BackgroundTask
from fastapi.responses import FileResponse
import os, time, traceback

from app.core.logging import logger, log_action
from app.schemas.export_docx import ExportPayload
from app.services.docx_export import generate_docx
from app.routes.pages import token_required

DEBUG = os.getenv("APP_DEBUG", "0") == "1"

router = APIRouter(prefix="/api/pages", tags=["export"])
export_router = APIRouter(prefix="/api/exports", tags=["exports"])

def _send_docx(tmp_path: str, filename: str) -> FileResponse:
    # 삭제는 FileResponse의 background에 연결 (응답 전송 완료 후 실행 보장)
    return FileResponse(
        path=tmp_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
        background=BackgroundTask(lambda p: os.path.exists(p) and os.remove(p), tmp_path),
    )

@router.post("/export_docx")
async def export_docx_legacy(
    payload: ExportPayload,
    request: Request,
    user=Depends(token_required),
):
    t0 = time.time()
    try:
        tmp_path, filename = generate_docx(payload)  # 반드시 절대경로 반환
        elapsed = int((time.time() - t0) * 1000)
        log_action(logger, getattr(request.state, "req_id", None), user.get("user_seq"),
                   None, "export_docx", elapsed, "0", None)
        return _send_docx(tmp_path, filename)

    except HTTPException:
        raise
    except Exception as e:
        elapsed = int((time.time() - t0) * 1000)
        log_action(logger, getattr(request.state, "req_id", None), user.get("user_seq"),
                   None, "export_docx", elapsed, "9",
                   f"EXPORT_FAILED: {e}\n{traceback.format_exc()}")
        if DEBUG:
            raise HTTPException(status_code=500, detail=f"[DEBUG] DOCX 생성 실패: {e}")
        raise HTTPException(status_code=500, detail="DOCX 생성 실패")

@export_router.post("/docx")
async def export_docx(payload: ExportPayload, request: Request, user=Depends(token_required)):
    return await export_docx_legacy(payload, request, user)
