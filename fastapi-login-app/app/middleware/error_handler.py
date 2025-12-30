"""
전역 에러 핸들러
모든 예외를 일관된 형식으로 처리
"""
import logging
import traceback
from typing import Callable

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.core.exceptions import AppException
from app.core.settings import settings

logger = logging.getLogger(__name__)


def setup_exception_handlers(app: FastAPI) -> None:
    """
    애플리케이션에 전역 예외 핸들러 등록

    Args:
        app: FastAPI 애플리케이션 인스턴스
    """

    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request,
        exc: AppException
    ) -> JSONResponse:
        """
        커스텀 AppException 처리
        애플리케이션에서 정의한 모든 예외를 처리
        """
        trace_id = getattr(request.state, "trace_id", None)

        # 로깅 (4xx는 warning, 5xx는 error)
        log_level = logging.WARNING if exc.status_code < 500 else logging.ERROR
        logger.log(
            log_level,
            exc.code,
            extra={
                "trace_id": trace_id,
                "message": exc.message,
                "status_code": exc.status_code,
                "details": exc.details,
                "path": str(request.url.path),
                "method": request.method,
            }
        )

        content = {
            "code": exc.code,
            "message": exc.message,
        }

        if trace_id:
            content["trace_id"] = trace_id

        if exc.details and settings.DEBUG:
            content["details"] = exc.details

        return JSONResponse(
            status_code=exc.status_code,
            content=content
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError
    ) -> JSONResponse:
        """
        Pydantic 검증 오류 처리
        요청 데이터 검증 실패 시 사용자 친화적 메시지 반환
        """
        trace_id = getattr(request.state, "trace_id", None)

        # 에러 세부 정보 추출
        errors = []
        for error in exc.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            errors.append({
                "field": field,
                "message": error["msg"],
                "type": error["type"]
            })

        logger.warning(
            "validation_error",
            extra={
                "trace_id": trace_id,
                "path": str(request.url.path),
                "errors": errors,
            }
        )

        content = {
            "code": "VALIDATION_ERROR",
            "message": "입력값이 올바르지 않습니다.",
            "errors": errors,
        }

        if trace_id:
            content["trace_id"] = trace_id

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=content
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_handler(
        request: Request,
        exc: ValidationError
    ) -> JSONResponse:
        """
        Pydantic 모델 검증 오류 처리
        """
        trace_id = getattr(request.state, "trace_id", None)

        errors = [
            {
                "field": " -> ".join(str(loc) for loc in e["loc"]),
                "message": e["msg"]
            }
            for e in exc.errors()
        ]

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "code": "VALIDATION_ERROR",
                "message": "데이터 검증에 실패했습니다.",
                "errors": errors,
                "trace_id": trace_id,
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request,
        exc: Exception
    ) -> JSONResponse:
        """
        예상치 못한 일반 예외 처리
        모든 처리되지 않은 예외를 잡아서 안전하게 응답
        """
        trace_id = getattr(request.state, "trace_id", None)

        # 상세 로깅
        logger.error(
            "unhandled_exception",
            extra={
                "trace_id": trace_id,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "path": str(request.url.path),
                "method": request.method,
            },
            exc_info=True
        )

        # 개발 환경에서는 상세 정보 표시
        if settings.DEBUG:
            detail = f"{type(exc).__name__}: {str(exc)}"
            stack_trace = traceback.format_exc()
        else:
            detail = "서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
            stack_trace = None

        content = {
            "code": "INTERNAL_SERVER_ERROR",
            "message": detail,
        }

        if trace_id:
            content["trace_id"] = trace_id

        if stack_trace and settings.DEBUG:
            content["stack_trace"] = stack_trace

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=content
        )


def create_error_response(
    code: str,
    message: str,
    status_code: int = 500,
    trace_id: str = None,
    details: dict = None
) -> JSONResponse:
    """
    에러 응답 생성 헬퍼 함수

    Args:
        code: 에러 코드
        message: 에러 메시지
        status_code: HTTP 상태 코드
        trace_id: 추적 ID
        details: 추가 세부 정보

    Returns:
        JSONResponse
    """
    content = {
        "code": code,
        "message": message,
    }

    if trace_id:
        content["trace_id"] = trace_id

    if details and settings.DEBUG:
        content["details"] = details

    return JSONResponse(
        status_code=status_code,
        content=content
    )
