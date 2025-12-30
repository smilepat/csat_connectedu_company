"""
커스텀 예외 클래스 정의
일관된 에러 처리를 위한 예외 계층 구조
"""
from typing import Any, Dict, Optional
from fastapi import status

from app.core.constants import ErrorCodes, ErrorMessages


class AppException(Exception):
    """
    기본 애플리케이션 예외
    모든 커스텀 예외의 베이스 클래스
    """

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """예외를 딕셔너리로 변환"""
        result = {
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result


# ===========================================
# 인증 관련 예외
# ===========================================

class AuthenticationError(AppException):
    """인증 실패 예외"""

    def __init__(
        self,
        message: str = ErrorMessages.AUTH_REQUIRED,
        code: str = ErrorCodes.VALIDATION_FAILED,
        login_url: str = "/login"
    ):
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details={"login_url": login_url}
        )


class TokenExpiredError(AuthenticationError):
    """토큰 만료 예외"""

    def __init__(self, message: str = ErrorMessages.AUTH_EXPIRED):
        super().__init__(
            message=message,
            code="AUTH_EXPIRED"
        )


class TokenInvalidError(AuthenticationError):
    """토큰 무효 예외"""

    def __init__(self, message: str = ErrorMessages.AUTH_INVALID):
        super().__init__(
            message=message,
            code="AUTH_INVALID"
        )


class TokenCorruptError(AuthenticationError):
    """토큰 손상 예외"""

    def __init__(self, message: str = "세션 데이터가 손상되었습니다."):
        super().__init__(
            message=message,
            code="AUTH_CORRUPT"
        )


# ===========================================
# 검증 관련 예외
# ===========================================

class ValidationError(AppException):
    """입력 검증 실패 예외"""

    def __init__(
        self,
        message: str = ErrorMessages.INVALID_INPUT,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            code=ErrorCodes.VALIDATION_FAILED,
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


# ===========================================
# 리소스 관련 예외
# ===========================================

class NotFoundError(AppException):
    """리소스를 찾을 수 없음"""

    def __init__(
        self,
        resource: str,
        resource_id: Any,
        message: Optional[str] = None
    ):
        msg = message or f"{resource} {resource_id}을(를) 찾을 수 없습니다."
        super().__init__(
            code=f"{resource.upper()}_NOT_FOUND",
            message=msg,
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource": resource, "id": str(resource_id)}
        )


class ItemNotFoundError(NotFoundError):
    """문항을 찾을 수 없음"""

    def __init__(self, item_id: Any):
        super().__init__(
            resource="Item",
            resource_id=item_id,
            message=ErrorMessages.ITEM_NOT_FOUND
        )


class PageNotFoundError(NotFoundError):
    """페이지를 찾을 수 없음"""

    def __init__(self, page_id: Any):
        super().__init__(
            resource="Page",
            resource_id=page_id,
            message=ErrorMessages.PAGE_NOT_FOUND
        )


# ===========================================
# 외부 서비스 관련 예외
# ===========================================

class ExternalServiceError(AppException):
    """외부 서비스 호출 실패"""

    def __init__(
        self,
        service: str,
        message: str,
        original_error: Optional[Exception] = None
    ):
        msg = f"{service} 서비스 오류: {message}"
        details = {"service": service}
        if original_error:
            details["original_error"] = str(original_error)

        super().__init__(
            code=ErrorCodes.EXTERNAL_SERVICE_ERROR,
            message=msg,
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details
        )


class JavaAPIError(ExternalServiceError):
    """Java API 호출 실패"""

    def __init__(
        self,
        endpoint: str,
        message: str = "Java API 요청에 실패했습니다.",
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            service="Java API",
            message=message,
            original_error=original_error
        )
        self.details["endpoint"] = endpoint


class LLMAPIError(ExternalServiceError):
    """LLM API 호출 실패"""

    def __init__(
        self,
        provider: str,
        message: str = "LLM API 요청에 실패했습니다.",
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            service=f"LLM ({provider})",
            message=message,
            original_error=original_error
        )


class RedisError(AppException):
    """Redis 오류"""

    def __init__(
        self,
        message: str = ErrorMessages.REDIS_ERROR,
        original_error: Optional[Exception] = None
    ):
        details = {}
        if original_error:
            details["original_error"] = str(original_error)

        super().__init__(
            code=ErrorCodes.REDIS_ERROR,
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


# ===========================================
# 비즈니스 로직 예외
# ===========================================

class ItemGenerationError(AppException):
    """문항 생성 실패"""

    def __init__(
        self,
        message: str = "문항 생성에 실패했습니다.",
        item_type: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        details = {}
        if item_type:
            details["item_type"] = item_type
        if original_error:
            details["original_error"] = str(original_error)

        super().__init__(
            code="ITEM_GENERATION_FAILED",
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class RateLimitError(AppException):
    """요청 제한 초과"""

    def __init__(
        self,
        message: str = "요청 제한을 초과했습니다. 잠시 후 다시 시도하세요.",
        retry_after: Optional[int] = None
    ):
        details = {}
        if retry_after:
            details["retry_after"] = retry_after

        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details
        )
