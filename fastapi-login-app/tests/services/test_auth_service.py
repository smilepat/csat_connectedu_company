"""
AuthService 테스트
인증 서비스 단위 테스트
"""
import pytest
import json
from unittest.mock import Mock, patch

from app.services.auth_service import AuthService
from app.core.exceptions import (
    TokenExpiredError,
    TokenInvalidError,
    TokenCorruptError,
    RedisError
)


class TestAuthServiceInit:
    """AuthService 초기화 테스트"""

    def test_init_success(self, mock_redis):
        """정상 초기화"""
        with patch("app.services.auth_service.redis.Redis", return_value=mock_redis):
            service = AuthService()
            assert service.ttl == 86400
            mock_redis.ping.assert_called_once()

    def test_init_redis_connection_error(self):
        """Redis 연결 실패 시 예외"""
        with patch("app.services.auth_service.redis.Redis") as mock:
            import redis
            mock.return_value.ping.side_effect = redis.ConnectionError("Connection refused")

            with pytest.raises(RedisError):
                AuthService()


class TestCreateSession:
    """세션 생성 테스트"""

    def test_create_session_success(self, mock_redis, mock_user):
        """세션 생성 성공"""
        with patch("app.services.auth_service.redis.Redis", return_value=mock_redis):
            service = AuthService()
            token = service.create_session(mock_user)

            assert token is not None
            assert len(token) == 36  # UUID 형식
            mock_redis.setex.assert_called_once()

    def test_create_session_redis_error(self, mock_redis, mock_user):
        """Redis 오류 시 예외"""
        import redis as redis_lib
        mock_redis.setex.side_effect = redis_lib.RedisError("Connection lost")

        with patch("app.services.auth_service.redis.Redis", return_value=mock_redis):
            service = AuthService()

            with pytest.raises(RedisError):
                service.create_session(mock_user)


class TestVerifyToken:
    """토큰 검증 테스트"""

    def test_verify_token_success(self, mock_redis, mock_user):
        """유효한 토큰 검증"""
        mock_redis.get.return_value = json.dumps(mock_user)

        with patch("app.services.auth_service.redis.Redis", return_value=mock_redis):
            service = AuthService()
            result = service.verify_token("valid-token")

            assert result["user_seq"] == mock_user["user_seq"]
            assert result["name"] == mock_user["name"]

    def test_verify_token_empty(self, mock_redis):
        """빈 토큰"""
        with patch("app.services.auth_service.redis.Redis", return_value=mock_redis):
            service = AuthService()

            with pytest.raises(TokenInvalidError):
                service.verify_token("")

    def test_verify_token_expired(self, mock_redis):
        """만료된 토큰"""
        mock_redis.get.return_value = None

        with patch("app.services.auth_service.redis.Redis", return_value=mock_redis):
            service = AuthService()

            with pytest.raises(TokenExpiredError):
                service.verify_token("expired-token")

    def test_verify_token_corrupt_data(self, mock_redis):
        """손상된 세션 데이터"""
        mock_redis.get.return_value = "not-valid-json"

        with patch("app.services.auth_service.redis.Redis", return_value=mock_redis):
            service = AuthService()

            with pytest.raises(TokenCorruptError):
                service.verify_token("corrupt-token")

    def test_verify_token_invalid_json_type(self, mock_redis):
        """잘못된 JSON 타입 (dict가 아닌 경우)"""
        mock_redis.get.return_value = json.dumps(["array", "not", "dict"])

        with patch("app.services.auth_service.redis.Redis", return_value=mock_redis):
            service = AuthService()

            with pytest.raises(TokenCorruptError):
                service.verify_token("invalid-type-token")


class TestRefreshSession:
    """세션 갱신 테스트"""

    def test_refresh_session_success(self, mock_redis):
        """세션 TTL 갱신 성공"""
        mock_redis.expire.return_value = True

        with patch("app.services.auth_service.redis.Redis", return_value=mock_redis):
            service = AuthService()
            result = service.refresh_session("valid-token")

            assert result == True
            mock_redis.expire.assert_called_once()

    def test_refresh_session_not_found(self, mock_redis):
        """존재하지 않는 세션 갱신"""
        mock_redis.expire.return_value = False

        with patch("app.services.auth_service.redis.Redis", return_value=mock_redis):
            service = AuthService()
            result = service.refresh_session("nonexistent-token")

            assert result == False


class TestDeleteSession:
    """세션 삭제 테스트"""

    def test_delete_session_success(self, mock_redis):
        """세션 삭제 성공"""
        mock_redis.delete.return_value = 1

        with patch("app.services.auth_service.redis.Redis", return_value=mock_redis):
            service = AuthService()
            result = service.delete_session("valid-token")

            assert result == True

    def test_delete_session_not_found(self, mock_redis):
        """존재하지 않는 세션 삭제"""
        mock_redis.delete.return_value = 0

        with patch("app.services.auth_service.redis.Redis", return_value=mock_redis):
            service = AuthService()
            result = service.delete_session("nonexistent-token")

            assert result == False


class TestGetSessionTTL:
    """세션 TTL 조회 테스트"""

    def test_get_session_ttl_valid(self, mock_redis):
        """유효한 세션 TTL 조회"""
        mock_redis.ttl.return_value = 3600

        with patch("app.services.auth_service.redis.Redis", return_value=mock_redis):
            service = AuthService()
            ttl = service.get_session_ttl("valid-token")

            assert ttl == 3600

    def test_get_session_ttl_no_key(self, mock_redis):
        """존재하지 않는 키"""
        mock_redis.ttl.return_value = -2

        with patch("app.services.auth_service.redis.Redis", return_value=mock_redis):
            service = AuthService()
            ttl = service.get_session_ttl("nonexistent-token")

            assert ttl == -2
