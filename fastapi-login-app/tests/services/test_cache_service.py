"""
CacheService 테스트
캐시 서비스 단위 테스트
"""
import pytest
import json
from unittest.mock import Mock, patch

from app.services.cache_service import CacheService, get_cache_service


class TestCacheServiceInit:
    """CacheService 초기화 테스트"""

    def test_init_success(self, mock_redis):
        """정상 초기화"""
        with patch("app.services.cache_service.redis.Redis", return_value=mock_redis):
            service = CacheService()
            assert service.is_available == True

    def test_init_redis_unavailable(self):
        """Redis 연결 실패 시 비활성화"""
        import redis as redis_lib

        with patch("app.services.cache_service.redis.Redis") as mock:
            mock.return_value.ping.side_effect = redis_lib.ConnectionError()
            service = CacheService()
            assert service.is_available == False


class TestCacheGet:
    """캐시 조회 테스트"""

    def test_get_success(self, mock_redis):
        """캐시 조회 성공"""
        test_data = {"key": "value", "count": 42}
        mock_redis.get.return_value = json.dumps(test_data)

        with patch("app.services.cache_service.redis.Redis", return_value=mock_redis):
            service = CacheService()
            result = service.get("test-key")

            assert result == test_data

    def test_get_not_found(self, mock_redis):
        """캐시 미스"""
        mock_redis.get.return_value = None

        with patch("app.services.cache_service.redis.Redis", return_value=mock_redis):
            service = CacheService()
            result = service.get("nonexistent-key")

            assert result is None

    def test_get_unavailable(self):
        """Redis 비활성화 상태에서 조회"""
        import redis as redis_lib

        with patch("app.services.cache_service.redis.Redis") as mock:
            mock.return_value.ping.side_effect = redis_lib.ConnectionError()
            service = CacheService()
            result = service.get("any-key")

            assert result is None


class TestCacheSet:
    """캐시 저장 테스트"""

    def test_set_success(self, mock_redis):
        """캐시 저장 성공"""
        mock_redis.setex.return_value = True

        with patch("app.services.cache_service.redis.Redis", return_value=mock_redis):
            service = CacheService()
            result = service.set("test-key", {"data": "value"})

            assert result == True
            mock_redis.setex.assert_called_once()

    def test_set_with_custom_ttl(self, mock_redis):
        """커스텀 TTL로 저장"""
        with patch("app.services.cache_service.redis.Redis", return_value=mock_redis):
            service = CacheService()
            service.set("test-key", {"data": "value"}, ttl=7200)

            call_args = mock_redis.setex.call_args
            assert call_args[0][1] == 7200  # TTL 확인

    def test_set_unavailable(self):
        """Redis 비활성화 상태에서 저장"""
        import redis as redis_lib

        with patch("app.services.cache_service.redis.Redis") as mock:
            mock.return_value.ping.side_effect = redis_lib.ConnectionError()
            service = CacheService()
            result = service.set("any-key", {"data": "value"})

            assert result == False


class TestCacheDelete:
    """캐시 삭제 테스트"""

    def test_delete_success(self, mock_redis):
        """캐시 삭제 성공"""
        mock_redis.delete.return_value = 1

        with patch("app.services.cache_service.redis.Redis", return_value=mock_redis):
            service = CacheService()
            result = service.delete("test-key")

            assert result == True

    def test_delete_pattern(self, mock_redis):
        """패턴 삭제"""
        mock_redis.keys.return_value = ["key1", "key2", "key3"]
        mock_redis.delete.return_value = 3

        with patch("app.services.cache_service.redis.Redis", return_value=mock_redis):
            service = CacheService()
            count = service.delete_pattern("cache:items:*")

            assert count == 3


class TestCacheGetOrSet:
    """get_or_set 테스트"""

    def test_get_or_set_cache_hit(self, mock_redis):
        """캐시 히트"""
        cached_data = {"cached": True}
        mock_redis.get.return_value = json.dumps(cached_data)

        with patch("app.services.cache_service.redis.Redis", return_value=mock_redis):
            service = CacheService()

            factory_called = False
            def factory():
                nonlocal factory_called
                factory_called = True
                return {"new": "data"}

            result = service.get_or_set("test-key", factory)

            assert result == cached_data
            assert factory_called == False  # factory가 호출되지 않아야 함

    def test_get_or_set_cache_miss(self, mock_redis):
        """캐시 미스"""
        mock_redis.get.return_value = None

        with patch("app.services.cache_service.redis.Redis", return_value=mock_redis):
            service = CacheService()

            new_data = {"new": "data"}
            result = service.get_or_set("test-key", lambda: new_data)

            assert result == new_data
            mock_redis.setex.assert_called_once()


class TestCacheDecorator:
    """캐싱 데코레이터 테스트"""

    def test_cached_decorator_hit(self, mock_redis):
        """데코레이터 캐시 히트"""
        cached_data = {"cached": True}
        mock_redis.get.return_value = json.dumps(cached_data)

        with patch("app.services.cache_service.redis.Redis", return_value=mock_redis):
            service = CacheService()

            call_count = 0

            @service.cached("test_prefix")
            def expensive_function(arg1, arg2):
                nonlocal call_count
                call_count += 1
                return {"result": arg1 + arg2}

            result = expensive_function(1, 2)

            assert result == cached_data
            assert call_count == 0  # 원본 함수 호출되지 않음

    def test_cached_decorator_miss(self, mock_redis):
        """데코레이터 캐시 미스"""
        mock_redis.get.return_value = None

        with patch("app.services.cache_service.redis.Redis", return_value=mock_redis):
            service = CacheService()

            @service.cached("test_prefix", ttl=600)
            def expensive_function(arg1, arg2):
                return {"result": arg1 + arg2}

            result = expensive_function(1, 2)

            assert result == {"result": 3}
            mock_redis.setex.assert_called_once()


class TestMakeKey:
    """캐시 키 생성 테스트"""

    def test_make_key_simple(self, mock_redis):
        """간단한 키 생성"""
        with patch("app.services.cache_service.redis.Redis", return_value=mock_redis):
            service = CacheService()
            key = service._make_key("prefix", "arg1", "arg2")

            assert "prefix" in key
            assert "arg1" in key
            assert "arg2" in key

    def test_make_key_with_kwargs(self, mock_redis):
        """kwargs 포함 키 생성"""
        with patch("app.services.cache_service.redis.Redis", return_value=mock_redis):
            service = CacheService()
            key = service._make_key("prefix", user_id=123, page=1)

            assert "user_id=123" in key
            assert "page=1" in key

    def test_make_key_long_key_hashed(self, mock_redis):
        """긴 키는 해시됨"""
        with patch("app.services.cache_service.redis.Redis", return_value=mock_redis):
            service = CacheService()

            long_args = ["a" * 50 for _ in range(10)]
            key = service._make_key("prefix", *long_args)

            assert len(key) <= 250  # 적절한 길이로 제한
