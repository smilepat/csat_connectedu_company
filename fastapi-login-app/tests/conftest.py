"""
테스트 공통 설정 및 Fixtures
pytest의 conftest.py는 모든 테스트에서 공유되는 fixture를 정의
"""
import os
import sys
import json
import pytest
from typing import Dict, Any, Generator
from unittest.mock import Mock, patch, AsyncMock

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient


# ===========================================
# 환경 설정
# ===========================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """테스트 환경 설정"""
    os.environ["ENV"] = "test"
    os.environ["REDIS_HOST"] = "localhost"
    os.environ["REDIS_PORT"] = "6379"
    os.environ["REDIS_DB"] = "1"  # 테스트용 별도 DB
    yield


# ===========================================
# FastAPI 클라이언트
# ===========================================

@pytest.fixture(scope="module")
def app():
    """FastAPI 애플리케이션 인스턴스"""
    from app.main import app as fastapi_app
    return fastapi_app


@pytest.fixture(scope="module")
def client(app) -> Generator:
    """테스트 클라이언트"""
    with TestClient(app) as test_client:
        yield test_client


# ===========================================
# 인증 관련 Fixtures
# ===========================================

@pytest.fixture
def mock_user() -> Dict[str, Any]:
    """모의 사용자 정보"""
    return {
        "user_seq": 12345,
        "name": "테스트 사용자",
        "coaching_date": "2024-01-01",
        "role": "teacher"
    }


@pytest.fixture
def mock_token() -> str:
    """모의 인증 토큰"""
    return "test-token-12345-abcde"


@pytest.fixture
def auth_headers(mock_token: str) -> Dict[str, str]:
    """인증 헤더"""
    return {"Authorization": f"Bearer {mock_token}"}


@pytest.fixture
def mock_auth_service(mock_user: Dict[str, Any], mock_token: str):
    """AuthService 모킹"""
    with patch("app.services.auth_service.get_auth_service") as mock:
        service = Mock()
        service.verify_token.return_value = mock_user
        service.create_session.return_value = mock_token
        mock.return_value = service
        yield service


@pytest.fixture
def mock_current_user(app, mock_user: Dict[str, Any]):
    """
    get_current_user 의존성 오버라이드
    인증이 필요한 엔드포인트 테스트 시 사용
    """
    from app.services.auth_service import get_current_user

    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield mock_user
    app.dependency_overrides.clear()


# ===========================================
# Redis 관련 Fixtures
# ===========================================

@pytest.fixture
def mock_redis():
    """Redis 클라이언트 모킹"""
    with patch("redis.Redis") as mock:
        redis_instance = Mock()
        redis_instance.get.return_value = None
        redis_instance.setex.return_value = True
        redis_instance.delete.return_value = 1
        redis_instance.ping.return_value = True
        redis_instance.expire.return_value = True
        mock.return_value = redis_instance
        yield redis_instance


@pytest.fixture
def mock_redis_with_user(mock_redis, mock_user: Dict[str, Any], mock_token: str):
    """사용자 세션이 있는 Redis 모킹"""
    mock_redis.get.return_value = json.dumps(mock_user)
    return mock_redis


# ===========================================
# HTTP 클라이언트 Fixtures
# ===========================================

@pytest.fixture
def mock_java_api_response() -> Dict[str, Any]:
    """Java API 모의 응답"""
    return {
        "result": "0",
        "message": "success",
        "data": {}
    }


@pytest.fixture
def mock_http_client(mock_java_api_response):
    """HTTP 클라이언트 모킹"""
    with patch("app.services.async_http_client.AsyncHttpClient") as mock:
        client = AsyncMock()
        client.post.return_value = mock_java_api_response
        client.get.return_value = mock_java_api_response
        mock.return_value = client
        yield client


@pytest.fixture
def mock_requests(mock_java_api_response):
    """requests 라이브러리 모킹 (동기 코드용)"""
    with patch("requests.post") as mock_post, \
         patch("requests.get") as mock_get:

        response = Mock()
        response.status_code = 200
        response.json.return_value = mock_java_api_response

        mock_post.return_value = response
        mock_get.return_value = response

        yield {"post": mock_post, "get": mock_get}


# ===========================================
# 문항 관련 Fixtures
# ===========================================

@pytest.fixture
def sample_item_request() -> Dict[str, Any]:
    """샘플 문항 저장 요청"""
    return {
        "item_type": "RC22",
        "item_name": "주제/요지 파악",
        "difficulty": "medium",
        "topic": "환경",
        "passage": json.dumps({
            "passage": "This is a test passage about environment.",
            "question": "What is the main topic?",
            "options": ["Option 1", "Option 2", "Option 3", "Option 4", "Option 5"],
            "correct_answer": "1"
        })
    }


@pytest.fixture
def sample_item_response() -> Dict[str, Any]:
    """샘플 문항 응답"""
    return {
        "question_seq": 1001,
        "item_type": "RC22",
        "item_name": "주제/요지 파악",
        "difficulty": "medium",
        "topic": "환경",
        "passage": "{...}",
        "created_at": "2024-01-01T00:00:00"
    }


# ===========================================
# 페이지 관련 Fixtures
# ===========================================

@pytest.fixture
def sample_page_request() -> Dict[str, Any]:
    """샘플 페이지 생성 요청"""
    return {
        "title": "테스트 페이지",
        "description": "테스트용 페이지입니다.",
        "is_public": False
    }


@pytest.fixture
def sample_page_response() -> Dict[str, Any]:
    """샘플 페이지 응답"""
    return {
        "page_id": 100,
        "title": "테스트 페이지",
        "description": "테스트용 페이지입니다.",
        "status": "draft",
        "is_public": False,
        "created_at": "2024-01-01T00:00:00"
    }


# ===========================================
# 유틸리티 Fixtures
# ===========================================

@pytest.fixture
def capture_logs():
    """로그 캡처"""
    import logging

    class LogCapture(logging.Handler):
        def __init__(self):
            super().__init__()
            self.records = []

        def emit(self, record):
            self.records.append(record)

        def get_messages(self):
            return [self.format(r) for r in self.records]

    handler = LogCapture()
    logger = logging.getLogger()
    logger.addHandler(handler)
    yield handler
    logger.removeHandler(handler)


# ===========================================
# 비동기 테스트 지원
# ===========================================

@pytest.fixture
def anyio_backend():
    """anyio 백엔드 설정 (pytest-asyncio용)"""
    return "asyncio"
