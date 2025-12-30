"""
캐시 서비스
Redis 기반 캐싱 기능 제공
"""
import json
import logging
import hashlib
from typing import Any, Callable, Optional, TypeVar, Union
from functools import wraps

import redis

from app.core.constants import RedisKeys

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CacheService:
    """
    Redis 기반 캐싱 서비스
    자주 조회되는 데이터의 캐싱을 통해 성능 향상
    """

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        default_ttl: int = 3600  # 1시간
    ):
        self.default_ttl = default_ttl
        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True,
                socket_connect_timeout=3
            )
            self.redis_client.ping()
            self._available = True
        except redis.ConnectionError as e:
            logger.warning(f"Redis 캐시 연결 실패 (캐싱 비활성화): {e}")
            self._available = False

    @property
    def is_available(self) -> bool:
        """캐시 서비스 사용 가능 여부"""
        return self._available

    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """캐시 키 생성"""
        key_parts = [prefix]
        if args:
            key_parts.extend(str(a) for a in args)
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            key_parts.extend(f"{k}={v}" for k, v in sorted_kwargs)

        raw_key = ":".join(key_parts)

        # 키가 너무 길면 해시 사용
        if len(raw_key) > 200:
            hash_suffix = hashlib.md5(raw_key.encode()).hexdigest()[:16]
            return f"{RedisKeys.CACHE_PREFIX}{prefix}:{hash_suffix}"

        return f"{RedisKeys.CACHE_PREFIX}{raw_key}"

    def get(self, key: str) -> Optional[Any]:
        """
        캐시에서 데이터 조회

        Args:
            key: 캐시 키

        Returns:
            캐시된 데이터 또는 None
        """
        if not self._available:
            return None

        try:
            value = self.redis_client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.warning(f"캐시 조회 실패: {e}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        캐시에 데이터 저장

        Args:
            key: 캐시 키
            value: 저장할 데이터
            ttl: TTL (초), None이면 기본값 사용

        Returns:
            성공 여부
        """
        if not self._available:
            return False

        try:
            json_value = json.dumps(value, ensure_ascii=False)
            self.redis_client.setex(
                key,
                ttl or self.default_ttl,
                json_value
            )
            return True
        except (redis.RedisError, TypeError) as e:
            logger.warning(f"캐시 저장 실패: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        캐시 삭제

        Args:
            key: 캐시 키

        Returns:
            성공 여부
        """
        if not self._available:
            return False

        try:
            self.redis_client.delete(key)
            return True
        except redis.RedisError as e:
            logger.warning(f"캐시 삭제 실패: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        패턴과 일치하는 모든 캐시 삭제

        Args:
            pattern: 키 패턴 (예: "cache:items:*")

        Returns:
            삭제된 키 개수
        """
        if not self._available:
            return 0

        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except redis.RedisError as e:
            logger.warning(f"패턴 캐시 삭제 실패: {e}")
            return 0

    def get_or_set(
        self,
        key: str,
        factory: Callable[[], T],
        ttl: Optional[int] = None
    ) -> T:
        """
        캐시에서 조회하고, 없으면 factory 함수로 생성 후 캐시

        Args:
            key: 캐시 키
            factory: 데이터 생성 함수
            ttl: TTL (초)

        Returns:
            캐시된 데이터 또는 새로 생성된 데이터
        """
        cached = self.get(key)
        if cached is not None:
            return cached

        value = factory()
        self.set(key, value, ttl)
        return value

    def cached(
        self,
        prefix: str,
        ttl: Optional[int] = None
    ):
        """
        함수 결과 캐싱 데코레이터 (동기 함수용)

        사용법:
            @cache.cached("items_list", ttl=3600)
            def get_items(user_id: int, page: int) -> dict:
                ...
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                cache_key = self._make_key(prefix, *args, **kwargs)
                cached = self.get(cache_key)
                if cached is not None:
                    logger.debug(f"캐시 히트: {cache_key}")
                    return cached

                logger.debug(f"캐시 미스: {cache_key}")
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl)
                return result
            return wrapper
        return decorator

    def cached_async(
        self,
        prefix: str,
        ttl: Optional[int] = None
    ):
        """
        함수 결과 캐싱 데코레이터 (비동기 함수용)

        사용법:
            @cache.cached_async("items_list", ttl=3600)
            async def get_items(user_id: int, page: int) -> dict:
                ...
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                cache_key = self._make_key(prefix, *args, **kwargs)
                cached = self.get(cache_key)
                if cached is not None:
                    logger.debug(f"캐시 히트: {cache_key}")
                    return cached

                logger.debug(f"캐시 미스: {cache_key}")
                result = await func(*args, **kwargs)
                self.set(cache_key, result, ttl)
                return result
            return wrapper
        return decorator

    def invalidate(self, prefix: str, *args, **kwargs) -> bool:
        """
        특정 캐시 무효화

        Args:
            prefix: 캐시 프리픽스
            *args, **kwargs: 캐시 키 생성에 사용된 인자

        Returns:
            성공 여부
        """
        cache_key = self._make_key(prefix, *args, **kwargs)
        return self.delete(cache_key)


# ===========================================
# 싱글톤 인스턴스
# ===========================================
import os

_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """CacheService 싱글톤 인스턴스 반환"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService(
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("REDIS_PORT", 6379)),
            default_ttl=int(os.getenv("CACHE_TTL", 3600))
        )
    return _cache_service


# ===========================================
# 편의 함수
# ===========================================

def cache_key(*parts: Union[str, int]) -> str:
    """간단한 캐시 키 생성"""
    return f"{RedisKeys.CACHE_PREFIX}" + ":".join(str(p) for p in parts)


def cached(prefix: str, ttl: int = 3600):
    """
    캐싱 데코레이터 (전역 캐시 서비스 사용)

    사용법:
        @cached("items_list", ttl=3600)
        def get_items(user_id: int) -> dict:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_service = get_cache_service()
            return cache_service.cached(prefix, ttl)(func)(*args, **kwargs)
        return wrapper
    return decorator


def cached_async(prefix: str, ttl: int = 3600):
    """
    비동기 캐싱 데코레이터 (전역 캐시 서비스 사용)

    사용법:
        @cached_async("items_list", ttl=3600)
        async def get_items(user_id: int) -> dict:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_service = get_cache_service()
            return await cache_service.cached_async(prefix, ttl)(func)(*args, **kwargs)
        return wrapper
    return decorator
