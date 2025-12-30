"""
통합 인증 서비스
Redis 기반 세션 관리 및 토큰 검증
"""
import json
import uuid
import logging
from typing import Optional, Dict, Any

import redis
from fastapi import Header, HTTPException, status

from app.core.constants import RedisKeys, ErrorMessages, AuthCodes
from app.core.exceptions import (
    TokenExpiredError,
    TokenInvalidError,
    TokenCorruptError,
    RedisError
)

logger = logging.getLogger(__name__)


class AuthService:
    """
    인증 서비스
    Redis 기반 세션 관리 및 토큰 검증을 담당
    """

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        ttl: int = 86400  # 24시간
    ):
        self.ttl = ttl
        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True,
                socket_connect_timeout=3
            )
            # 연결 테스트
            self.redis_client.ping()
        except redis.ConnectionError as e:
            logger.error(f"Redis 연결 실패: {e}")
            raise RedisError("Redis 서버에 연결할 수 없습니다.", original_error=e)

    def create_session(self, user_info: Dict[str, Any]) -> str:
        """
        새로운 세션 생성

        Args:
            user_info: 사용자 정보 딕셔너리

        Returns:
            생성된 토큰
        """
        token = str(uuid.uuid4())
        key = RedisKeys.auth_session(token)

        try:
            self.redis_client.setex(
                key,
                self.ttl,
                json.dumps(user_info, ensure_ascii=False)
            )
            logger.info(f"세션 생성: user_seq={user_info.get('user_seq')}")
            return token
        except redis.RedisError as e:
            logger.error(f"세션 생성 실패: {e}")
            raise RedisError("세션 생성에 실패했습니다.", original_error=e)

    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        토큰을 검증하고 사용자 정보 반환

        Args:
            token: 인증 토큰

        Returns:
            사용자 정보 딕셔너리

        Raises:
            TokenExpiredError: 토큰이 만료됨
            TokenCorruptError: 세션 데이터 손상
            RedisError: Redis 오류
        """
        if not token:
            raise TokenInvalidError()

        key = RedisKeys.auth_session(token)

        try:
            user_data = self.redis_client.get(key)
        except redis.RedisError as e:
            logger.error(f"Redis 조회 오류: {e}")
            raise RedisError(original_error=e)

        if not user_data:
            raise TokenExpiredError()

        try:
            user_json = json.loads(user_data)
            if not isinstance(user_json, dict):
                raise ValueError("Invalid session payload")
            return user_json
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"세션 데이터 파싱 오류: {e}")
            raise TokenCorruptError()

    def refresh_session(self, token: str) -> bool:
        """
        세션 TTL 갱신

        Args:
            token: 인증 토큰

        Returns:
            성공 여부
        """
        key = RedisKeys.auth_session(token)
        try:
            return self.redis_client.expire(key, self.ttl)
        except redis.RedisError as e:
            logger.error(f"세션 갱신 실패: {e}")
            return False

    def delete_session(self, token: str) -> bool:
        """
        세션 삭제 (로그아웃)

        Args:
            token: 인증 토큰

        Returns:
            성공 여부
        """
        key = RedisKeys.auth_session(token)
        try:
            result = self.redis_client.delete(key)
            return result > 0
        except redis.RedisError as e:
            logger.error(f"세션 삭제 실패: {e}")
            return False

    def get_session_ttl(self, token: str) -> int:
        """
        세션 남은 TTL 조회

        Args:
            token: 인증 토큰

        Returns:
            남은 TTL (초), -2면 키 없음, -1면 TTL 없음
        """
        key = RedisKeys.auth_session(token)
        try:
            return self.redis_client.ttl(key)
        except redis.RedisError:
            return -2


# ===========================================
# 싱글톤 인스턴스
# ===========================================
import os

_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """AuthService 싱글톤 인스턴스 반환"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService(
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("REDIS_PORT", 6379)),
            ttl=int(os.getenv("REDIS_TTL", 86400))
        )
    return _auth_service


# ===========================================
# FastAPI 의존성
# ===========================================

def get_current_user(authorization: str = Header(None)) -> Dict[str, Any]:
    """
    FastAPI 의존성: 현재 인증된 사용자 정보 반환

    사용법:
        @router.get("/protected")
        def protected_route(user: dict = Depends(get_current_user)):
            return {"user": user}
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": ErrorMessages.AUTH_REQUIRED,
                "code": AuthCodes.AUTH_REQUIRED,
                "login_url": "/login"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "Bearer 토큰 형식이 필요합니다.",
                "code": AuthCodes.AUTH_INVALID,
                "login_url": "/login"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = authorization.replace("Bearer ", "", 1).strip()

    try:
        auth_service = get_auth_service()
        return auth_service.verify_token(token)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": ErrorMessages.AUTH_EXPIRED,
                "code": AuthCodes.AUTH_EXPIRED,
                "login_url": "/login"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    except TokenCorruptError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": "세션 데이터가 손상되었습니다.",
                "code": AuthCodes.AUTH_CORRUPT,
                "login_url": "/login"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    except RedisError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": ErrorMessages.REDIS_ERROR}
        )


def get_current_user_optional(
    authorization: str = Header(None)
) -> Optional[Dict[str, Any]]:
    """
    FastAPI 의존성: 선택적 인증
    토큰이 없어도 None 반환 (에러 없음)
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.replace("Bearer ", "", 1).strip()

    try:
        auth_service = get_auth_service()
        return auth_service.verify_token(token)
    except Exception:
        return None
