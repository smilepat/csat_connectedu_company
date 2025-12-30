"""
인증 라우트 테스트
/api/auth 엔드포인트 테스트
"""
import pytest
import json
from unittest.mock import patch, Mock


class TestLogin:
    """로그인 테스트"""

    def test_login_success(self, client, mock_redis, mock_requests):
        """로그인 성공 테스트"""
        # Java API 응답 모킹
        mock_requests["post"].return_value.json.return_value = {
            "coach_info": {
                "user_seq": 12345,
                "name": "테스트 사용자",
                "coaching_date": "2024-01-01",
                "role": "teacher"
            }
        }

        response = client.post(
            "/api/auth/login",
            json={"user_id": "testuser", "password": "testpass"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["message"] == "로그인 성공"
        assert data["user"]["name"] == "테스트 사용자"

    def test_login_invalid_credentials(self, client, mock_requests):
        """잘못된 자격 증명 테스트"""
        mock_requests["post"].return_value.json.return_value = {
            "error": "Invalid credentials"
        }

        response = client.post(
            "/api/auth/login",
            json={"user_id": "wronguser", "password": "wrongpass"}
        )

        assert response.status_code == 500

    def test_login_missing_fields(self, client):
        """필수 필드 누락 테스트"""
        response = client.post(
            "/api/auth/login",
            json={"user_id": "testuser"}  # password 누락
        )

        assert response.status_code == 422  # Validation Error


class TestDashboard:
    """대시보드 테스트"""

    def test_dashboard_authenticated(self, client, mock_current_user):
        """인증된 사용자 대시보드 접근"""
        response = client.get(
            "/api/auth/dashboard",
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "테스트 사용자" in data["message"]

    def test_dashboard_no_token(self, client):
        """토큰 없이 대시보드 접근"""
        response = client.get("/api/auth/dashboard")

        assert response.status_code == 401

    def test_dashboard_invalid_token(self, client, mock_redis):
        """유효하지 않은 토큰으로 대시보드 접근"""
        mock_redis.get.return_value = None

        response = client.get(
            "/api/auth/dashboard",
            headers={"Authorization": "Bearer invalid-token"}
        )

        assert response.status_code == 401


class TestTokenValidation:
    """토큰 검증 테스트"""

    def test_bearer_prefix_required(self, client):
        """Bearer 접두사 필수 테스트"""
        response = client.get(
            "/api/auth/dashboard",
            headers={"Authorization": "test-token"}  # Bearer 없음
        )

        assert response.status_code == 401

    def test_empty_token(self, client):
        """빈 토큰 테스트"""
        response = client.get(
            "/api/auth/dashboard",
            headers={"Authorization": "Bearer "}
        )

        assert response.status_code == 401
