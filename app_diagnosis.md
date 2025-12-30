# FastAPI 앱 자가진단 및 개선점 보고서

## 종합 평가

| 카테고리 | 현황 | 우선순위 |
|----------|------|----------|
| 보안 | ⚠️ 낮음 | 🔴 높음 |
| 코드 품질 | 🟡 중간 | 🔴 높음 |
| 아키텍처 | ⚠️ 낮음 | 🔴 높음 |
| 테스트 | ❌ 없음 | 🔴 높음 |
| 문서화 | 🟡 최소한 | 🟡 중간 |
| 성능 | 🟡 중간 | 🟡 중간 |
| 모니터링 | ❌ 없음 | 🟡 중간 |

---

## 1. 코드 품질 분석

### 1.1 코드 중복 (Code Duplication)

**문제점:**

1. **인증 로직 중복**: `auth.py`, `auth_utils.py`, `items.py`, `pages.py`에서 `token_required` 함수가 거의 동일하게 반복됨

2. **외부 API 호출 패턴 중복**: `items.py`와 `pages.py`에서 Java API 호출이 유사한 방식으로 반복
   - 동일한 헤더 구성
   - 동일한 에러 핸들링
   - 동일한 요청/응답 형식

3. **Redis 클라이언트 초기화 중복**:
   ```python
   # items.py
   r = redis.Redis(host='localhost', port=6379, db=0)

   # pages.py
   r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
   ```

**개선 방안:**

```python
# app/services/auth_service.py (새 파일)
from fastapi import Header, HTTPException, status
import json
import redis
from app.core.settings import settings

class AuthService:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST or "localhost",
            port=settings.REDIS_PORT or 6379,
            decode_responses=True
        )

    def verify_token(self, token: str) -> dict:
        """토큰을 검증하고 사용자 정보 반환"""
        user_data = self.redis_client.get(f"auth:{token}")
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": "세션이 만료되었습니다.",
                    "code": "AUTH_EXPIRED",
                    "login_url": "/login"
                }
            )
        try:
            return json.loads(user_data)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="손상된 세션입니다"
            )

# app/dependencies.py (새 파일)
from fastapi import Depends, Header
from app.services.auth_service import AuthService

auth_service = AuthService()

def get_current_user(authorization: str = Header(None)):
    """의존성 주입을 통해 인증된 사용자 정보 반환"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="인증 토큰이 필요합니다")

    token = authorization.replace("Bearer ", "", 1).strip()
    return auth_service.verify_token(token)

# 라우터에서 사용
@router.get("/list")
def get_items_list(user=Depends(get_current_user), page: int = Query(1)):
    ...
```

### 1.2 함수/클래스 복잡도

**문제점:**

1. **`item_generator.py` (508줄)**: 너무 많은 책임
   - JSON 파싱, 스키마 검증, LLM 호출, 재시도 로직, 폴백 처리 모두 포함

2. **`pages.py` (279줄)**: 여러 엔드포인트와 로직이 혼재

3. **`docx_export.py`**: 매우 긴 단일 파일

**개선 방안:**

```python
# app/services/item_generator.py - 리팩토링
class ItemGeneratorPipeline:
    """문항 생성 파이프라인 - 단일 책임 원칙"""
    def __init__(self, llm_client, spec_registry, logger):
        self.llm_client = llm_client
        self.spec_registry = spec_registry
        self.logger = logger

    async def generate(self, item_id: str, payload: dict, trace_id: str):
        """전체 파이프라인 오케스트레이션"""
        spec = self._get_spec(item_id)
        messages = self._build_messages(spec, payload)
        raw_response = await self.llm_client.call(messages, trace_id=trace_id)
        parsed = self._parse_response(raw_response)
        validated = self._validate(parsed, spec)
        return validated

class ResponseParser:
    """JSON 파싱 전담"""
    @staticmethod
    def parse(raw: str) -> dict:
        ...

class SpecValidator:
    """스키마 검증 전담"""
    @staticmethod
    def validate(data: dict, spec) -> dict:
        ...
```

### 1.3 네이밍 컨벤션

**문제점:**

1. **불일치한 변수명**: `item_id` vs `itemId` (snake_case vs camelCase 혼용)

2. **약어 과다 사용**: `req`, `resp`, `msg`, `exc`, `seq`

3. **매직 문자열**: `"coach_info"`, `"auth:{token}"` 등 상수로 정의되지 않음

**개선 방안:**

```python
# app/constants.py (새 파일)
class RedisKeys:
    """Redis 키 상수"""
    AUTH_SESSION = "auth:{token}"
    USER_PROFILE = "profile:{user_id}"

class APIFields:
    """외부 API 응답 필드명"""
    COACH_INFO = "coach_info"
    USER_SEQ = "user_seq"
    COACHING_DATE = "coaching_date"

# 사용
user_data = r.get(RedisKeys.AUTH_SESSION.format(token=token))
if APIFields.COACH_INFO not in data:
    raise HTTPException(...)
```

### 1.4 타입 힌트 사용

**문제점:**

1. **누락된 타입 힌트**:
   ```python
   def get_item_detail(data: dict, token: dict = Depends(token_required)):
   # 반환 타입 없음, data 구조 불명확
   ```

**개선 방안:**

```python
# app/schemas/items.py - 추가
class ItemDetailRequest(BaseModel):
    """아이템 상세 조회 요청"""
    question_seq: int

class UserInfo(BaseModel):
    """사용자 정보"""
    user_seq: int
    name: str
    coaching_date: str
    role: str

# app/routes/items.py - 개선
from typing import Annotated
from app.schemas.items import ItemDetailRequest

@router.post("/detail")
def get_item_detail(
    data: ItemDetailRequest,
    user: Annotated[UserInfo, Depends(token_required)]
) -> dict[str, Any]:
    """아이템 상세 정보 조회"""
    ...
```

---

## 2. 아키텍처 분석

### 2.1 관심사 분리 (SoC) 문제

**문제점:**

1. **라우터와 비즈니스 로직 혼재**:
   ```python
   @router.post("/save")
   def save_item(item: ItemRequest, user=Depends(token_required)):
       payload = { ... }  # 데이터 변환 로직
       response = requests.post(...)  # API 호출
       if response.status_code == 200:
           return { ... }  # 응답 포맷팅
   ```

2. **외부 API 호출이 라우터에 직접 구현**

3. **설정과 런타임 코드 혼재**

**개선 방안:**

```python
# app/layers/application/item_use_case.py (새 파일)
"""비즈니스 로직 레이어"""
class SaveItemUseCase:
    def __init__(self, repository: ItemRepository):
        self.repository = repository

    def execute(self, user_id: int, item_data: dict) -> Item:
        """아이템 저장"""
        item = Item(
            user_id=user_id,
            difficulty=item_data['difficulty'],
            topic=item_data['topic'],
        )
        return self.repository.save(item)

# app/adapters/java_item_adapter.py (새 파일)
"""외부 API 어댑터"""
class JavaItemAdapter(ItemRepository):
    def __init__(self, base_url: str, auth: str):
        self.base_url = base_url
        self.auth = auth

    def save(self, item: Item) -> Item:
        """Java API를 통해 아이템 저장"""
        payload = self._to_java_format(item)
        response = requests.post(
            f"{self.base_url}/save",
            json=payload,
            headers=self._get_headers(),
            timeout=5,
            verify=False
        )
        return self._from_java_response(response.json())
```

### 2.2 의존성 관리

**문제점:**

1. **하드코딩된 외부 서비스 URL**
2. **Redis 클라이언트가 모듈 레벨에서 초기화**
3. **컨테이너/DI 프레임워크 부재**

**개선 방안:**

```python
# app/core/container.py (새 파일)
"""의존성 컨테이너"""
class Container:
    def __init__(self):
        self.redis = RedisAdapter(settings.REDIS_URL)
        self.auth_service = AuthService(self.redis)
        self.java_adapter = JavaItemAdapter(
            settings.JAVA_API_BASE_URL,
            settings.JAVA_BASIC_AUTH
        )

container = Container()

def get_auth_service():
    return container.auth_service

def get_java_adapter():
    return container.java_adapter
```

---

## 3. 보안 분석

### 3.1 인증/인가 구현

**문제점:**

1. **토큰 검증이 불완전**: UUID 토큰만 사용 (서명 없음)
2. **세션 정보가 평문 저장**
3. **사용자 권한 검증 부재**: 인증만 확인, 인가(authorization) 없음

**개선 방안:**

```python
# app/security/jwt_handler.py (새 파일)
import jwt
from datetime import datetime, timedelta

class JWTHandler:
    """JWT 기반 토큰 관리"""

    def create_token(self, user_id: int, expires_delta: timedelta = None) -> str:
        """JWT 토큰 생성"""
        if expires_delta is None:
            expires_delta = timedelta(hours=24)

        expire = datetime.utcnow() + expires_delta
        payload = {
            "sub": str(user_id),
            "exp": expire,
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

    def verify_token(self, token: str) -> dict:
        """JWT 토큰 검증"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="토큰이 만료되었습니다")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")

# app/security/permissions.py (새 파일)
from enum import Enum

class Permission(Enum):
    READ_ITEMS = "read:items"
    WRITE_ITEMS = "write:items"
    DELETE_ITEMS = "delete:items"
    ADMIN = "admin"

class Role(Enum):
    USER = [Permission.READ_ITEMS]
    EDITOR = [Permission.READ_ITEMS, Permission.WRITE_ITEMS]
    ADMIN = [Permission.ADMIN]
```

### 3.2 민감 정보 처리

**문제점:**

1. **.env 파일에 실제 인증정보 존재** (커밋됨)
2. **로그에 민감 정보 노출 가능**
3. **응답에 불필요한 정보 노출**

**개선 방안:**

```python
# app/core/logging.py - 민감정보 레덕션 개선
import re

class SensitiveDataRedactor:
    """민감 정보 자동 마스킹"""

    PATTERNS = [
        (r'("auth_key"\s*:\s*)"([^"]*)"', r'\1"***REDACTED***"'),
        (r'("password"\s*:\s*)"([^"]*)"', r'\1"***REDACTED***"'),
        (r'(Bearer\s+)([A-Za-z0-9\-\._~\+\/]+)', r'\1***REDACTED***'),
        (r'(Basic\s+)([A-Za-z0-9+/=]+)', r'\1***REDACTED***'),
    ]

    @classmethod
    def redact(cls, text: str) -> str:
        for pattern, replacement in cls.PATTERNS:
            text = re.sub(pattern, replacement, text)
        return text
```

### 3.3 입력 검증

**문제점:**

1. **Pydantic 검증이 최소한**: 길이 제한, 허용값 검증 없음
2. **외부 API 응답 검증 부재**
3. **경로 매개변수 검증 부족**

**개선 방안:**

```python
# app/schemas/items.py - 개선된 검증
from pydantic import BaseModel, Field, validator
from enum import Enum

class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class ItemRequest(BaseModel):
    item_type: str = Field(..., min_length=1, max_length=50)
    item_name: str = Field(..., min_length=1, max_length=200)
    difficulty: DifficultyLevel  # enum으로 제한
    topic: str = Field(..., min_length=1, max_length=500)
    passage: str = Field(..., max_length=10000)  # 최대 크기 제한

    @validator('item_type')
    def validate_item_type(cls, v):
        allowed_types = ['mc', 'short_answer', 'essay']
        if v not in allowed_types:
            raise ValueError(f'item_type must be one of {allowed_types}')
        return v
```

---

## 4. 성능 분석

### 4.1 비동기 처리

**문제점:**

1. **동기 함수에서 I/O 작업**: `requests` 라이브러리 사용 (블로킹)
2. **일부 라우터만 async**: 일관성 없음

**개선 방안:**

```python
# app/services/http_client.py - 비동기 HTTP 클라이언트
import httpx

class AsyncHttpClient:
    """비동기 HTTP 클라이언트"""

    def __init__(self, timeout: float = 5.0):
        self.client = httpx.AsyncClient(timeout=timeout)

    async def post(self, url: str, json: dict, headers: dict) -> dict:
        """비동기 POST 요청"""
        response = await self.client.post(url, json=json, headers=headers, verify=False)
        response.raise_for_status()
        return response.json()

# app/routes/items.py - 비동기 라우터로 변경
@router.get("/list")
async def get_items_list(
    user: Annotated[UserInfo, Depends(get_current_user)],
    page: int = Query(1, ge=1),
):
    """아이템 목록 조회 - 비동기"""
    http_client = AsyncHttpClient()
    result = await http_client.post(JAVA_LIST_URL, json=payload, headers=headers)
    return result
```

### 4.2 캐싱 전략

**문제점:**

1. **캐싱 없음**: 동일한 요청에 대해 매번 Java API 호출
2. **Redis를 세션 저장소로만 사용**

**개선 방안:**

```python
# app/services/cache_service.py (새 파일)
class CacheService:
    """Redis 기반 캐싱 서비스"""

    def __init__(self):
        self.redis = redis.Redis(url=settings.REDIS_URL, decode_responses=True)

    def cached(self, ttl: int = 3600):
        """데코레이터로 함수 결과 캐싱"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
                cached = self.redis.get(cache_key)
                if cached:
                    return json.loads(cached)
                result = await func(*args, **kwargs)
                self.redis.setex(cache_key, ttl, json.dumps(result))
                return result
            return wrapper
        return decorator

# 사용 예시
cache = CacheService()

@router.get("/items/{item_id}")
@cache.cached(ttl=3600)  # 1시간 캐싱
async def get_item(item_id: str):
    return await fetch_item_from_java(item_id)
```

---

## 5. 에러 처리 분석

### 5.1 예외 처리 일관성

**문제점:**

1. **광범위한 Exception 캐치**
2. **에러 처리가 라우터마다 다름**
3. **예외 정보 손실**

**개선 방안:**

```python
# app/exceptions.py (새 파일)
"""커스텀 예외 정의"""

class AppException(Exception):
    """기본 애플리케이션 예외"""
    def __init__(self, code: str, message: str, status_code: int = 500):
        self.code = code
        self.message = message
        self.status_code = status_code

class AuthenticationError(AppException):
    """인증 실패"""
    def __init__(self, message: str = "인증에 실패했습니다"):
        super().__init__("AUTH_FAILED", message, 401)

class ExternalServiceError(AppException):
    """외부 서비스 호출 실패"""
    def __init__(self, service: str, message: str):
        super().__init__("EXTERNAL_SERVICE_ERROR", f"{service} 오류: {message}", 502)

class ItemNotFoundError(AppException):
    """문항을 찾을 수 없음"""
    def __init__(self, item_id: str):
        super().__init__("ITEM_NOT_FOUND", f"문항 {item_id}을 찾을 수 없습니다", 404)

# app/middleware/error_handler.py (새 파일)
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """애플리케이션 예외 처리"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "trace_id": getattr(request.state, "trace_id", None)
        }
    )
```

### 5.2 사용자 친화적 에러 메시지

```python
# app/messages.py (새 파일)
ERROR_MESSAGES = {
    "AUTH_REQUIRED": "로그인이 필요합니다.",
    "AUTH_EXPIRED": "세션이 만료되었습니다. 다시 로그인하세요.",
    "INVALID_INPUT": "입력값이 올바르지 않습니다.",
    "ITEM_NOT_FOUND": "요청한 문항을 찾을 수 없습니다.",
    "ITEM_SAVE_FAILED": "문항 저장에 실패했습니다. 잠시 후 다시 시도하세요.",
    "API_UNAVAILABLE": "현재 서비스를 이용할 수 없습니다.",
}
```

---

## 6. 테스트 분석

### 현황
- 테스트 파일 없음
- 테스트 커버리지 0%

### 권장 테스트 구조

```
tests/
├── conftest.py              # 공통 fixture
├── routes/
│   ├── test_items.py
│   ├── test_auth.py
│   └── test_pages.py
└── services/
    ├── test_auth_service.py
    └── test_item_generator.py
```

### 테스트 예시

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_current_user

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_user():
    return {"user_seq": 123, "name": "테스트", "role": "user"}

@pytest.fixture
def mock_auth(mock_user):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides.clear()

# tests/routes/test_items.py
@pytest.mark.asyncio
async def test_get_items_list(client, mock_auth):
    response = client.get("/items/list", headers={"Authorization": "Bearer token"})
    assert response.status_code == 200

async def test_save_item_unauthorized(client):
    response = client.post("/items/save", json={...})
    assert response.status_code == 401
```

---

## 7. 문서화 분석

### 7.1 API 문서

**개선 방안:**

```python
# app/main.py - OpenAPI 개선
def custom_openapi():
    openapi_schema = get_openapi(
        title="ConnectedU ItemGen API",
        version="1.0.0",
        description="""
        ## 개요
        ConnectedU 문항 생성 및 관리 API

        ## 인증
        모든 API는 Bearer 토큰 인증이 필요합니다:
        ```
        Authorization: Bearer <your_token>
        ```
        """,
        routes=app.routes,
    )
    return openapi_schema

# 라우터에 상세 문서 추가
@router.post(
    "/save",
    summary="문항 저장",
    description="새로운 문항을 생성하고 저장합니다.",
    responses={
        200: {"description": "저장 성공"},
        401: {"description": "인증 필요"},
        500: {"description": "서버 오류"}
    }
)
async def save_item(item: ItemRequest):
    ...
```

---

## 8. DevOps/운영 분석

### 8.1 환경 설정 관리

**문제점:**

1. **.env 파일이 커밋됨** (보안 위험)
2. **환경별 설정 분리 없음**

**개선 방안:**

```python
# app/core/config.py
class DevelopmentConfig(BaseConfig):
    DEBUG: bool = True
    REDIS_URL: str = "redis://localhost:6379"

class ProductionConfig(BaseConfig):
    DEBUG: bool = False
    REDIS_URL: str = Field(..., validation_alias="REDIS_URL")

def get_config():
    env = os.getenv("ENV", "development")
    configs = {"development": DevelopmentConfig, "production": ProductionConfig}
    return configs.get(env, DevelopmentConfig)()
```

### 8.2 모니터링

**개선 방안:**

```python
# app/monitoring/metrics.py
from prometheus_client import Counter, Histogram

request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])
llm_calls = Counter('llm_calls_total', 'Total LLM calls', ['model', 'status'])

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "redis": _check_redis(),
        "external_api": _check_external_api(),
    }

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

### 8.3 배포 구성

```dockerfile
# Dockerfile
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
COPY app/ ./app/

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s CMD python -c "import requests; requests.get('http://localhost:8000/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - ENV=development
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

---

## 9. 개선 로드맵

### Phase 1: 긴급 개선 (1-2주)

| 작업 | 설명 | 우선순위 |
|------|------|----------|
| .gitignore 추가 | .env 파일 제외 | 🔴 |
| JWT 토큰 도입 | 서명된 토큰으로 변경 | 🔴 |
| token_required 통합 | 중복 제거 | 🔴 |
| 민감정보 로깅 제거 | 레덕션 적용 | 🔴 |

### Phase 2: 구조 개선 (2-3주)

| 작업 | 설명 | 우선순위 |
|------|------|----------|
| 레이어드 아키텍처 | Routes → Services → Adapters | 🟠 |
| 의존성 주입 컨테이너 | Container 클래스 구현 | 🟠 |
| 커스텀 예외 클래스 | 일관된 에러 처리 | 🟠 |
| 기본 테스트 작성 | 주요 라우터 테스트 | 🟠 |

### Phase 3: 운영성 개선 (3-4주)

| 작업 | 설명 | 우선순위 |
|------|------|----------|
| Prometheus 메트릭 | 모니터링 추가 | 🟡 |
| 헬스 체크 강화 | 외부 서비스 상태 확인 | 🟡 |
| Docker 이미지 | 컨테이너화 | 🟡 |
| CI/CD 파이프라인 | 자동 배포 | 🟡 |

### Phase 4: 성능 최적화 (4주 이상)

| 작업 | 설명 | 우선순위 |
|------|------|----------|
| 전체 async 전환 | requests → httpx | 🟢 |
| Redis 캐싱 전략 | 자주 사용되는 데이터 캐싱 | 🟢 |
| 커넥션 풀링 | Redis/HTTP 연결 최적화 | 🟢 |

---

## 10. 요약

이 프로젝트는 기능적으로 동작하는 FastAPI 애플리케이션이지만, 프로덕션 환경을 위해 다음 개선이 필요합니다:

### 즉시 해결 필요
1. **보안**: .env 파일 .gitignore 추가, JWT 도입
2. **코드 중복**: 인증 로직 통합
3. **테스트**: 기본 테스트 구조 마련

### 중기 개선
1. **아키텍처**: 레이어 분리, 의존성 주입
2. **성능**: 비동기 처리 일관성
3. **모니터링**: 메트릭, 헬스체크

### 장기 개선
1. **배포 자동화**: Docker, Kubernetes, CI/CD
2. **캐싱 전략**: Redis 활용 확대
3. **문서화**: API 문서, README 완성
