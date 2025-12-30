# CSAT 영어 문제 자동 생성 시스템 - 앱 구조 분석

## 1. 프로젝트 개요

- **프로젝트명**: fastapi-login-app
- **프로젝트 타입**: 백엔드 REST API (AI/LLM 통합)
- **주요 목적**: CSAT (수능) 영어 문제 자동 생성 및 관리 시스템
- **위치**: `f:\csat_connectedu_company\fastapi-login-app`

---

## 2. 기술 스택

### 프레임워크 & 서버
- **FastAPI 0.115.13**: 주요 웹 프레임워크
- **Uvicorn 0.34.3**: ASGI 서버
- **Gunicorn 23.0.0**: 프로덕션 WSGI 서버
- **Starlette 0.46.2**: FastAPI 의존 라이브러리

### 설정 & 검증
- **Pydantic 2.11.7**: 데이터 모델 검증
- **Pydantic Settings 2.10.1**: 환경 설정 관리
- **Python-dotenv 1.1.0**: .env 파일 로드
- **PyYAML 6.0.2**: YAML 처리

### 데이터베이스
- **SQLAlchemy 2.0.41**: ORM
- **Alembic 1.16.2**: 마이그레이션 관리

### 인증 & 보안
- **PyJWT 2.10.1**: JWT 토큰 처리
- **Redis 6.2.0**: 세션 저장소

### 외부 API & AI
- **OpenAI 1.99.9**: OpenAI API 클라이언트
- **Azure Core 1.35.0**: Azure SDK
- **Azure Identity 1.24.0**: Azure 인증
- **Azure Storage Blob 12.26.0**: Azure Blob Storage

### HTTP 통신
- **Requests 2.32.4**: HTTP 라이브러리
- **Httpx 0.28.1**: 비동기 HTTP 클라이언트
- **Tenacity 9.1.2**: 재시도 라이브러리
- **tqdm 4.67.1**: 진행률 표시

### 문서 처리
- **python-docx 1.2.0**: Word 문서 생성/편집
- **aiofiles 24.1.0**: 비동기 파일 I/O

---

## 3. 디렉토리 구조

```
f:\csat_connectedu_company\fastapi-login-app/
├── .env                          # 환경 설정 파일 (API 키, DB 정보 등)
├── requirements.txt              # Python 의존성
├── requirements_raw.txt          # 원본 의존성
├── prompts.json                  # 프롬프트 설정
├── structure_fastapi.txt         # 구조 문서
│
├── app/                          # 메인 애플리케이션 코드
│   ├── main.py                   # FastAPI 애플리케이션 진입점
│   ├── auth.py                   # 인증 로직 (로그인, JWT 토큰)
│   ├── auth_utils.py             # 인증 유틸리티
│   ├── models.py                 # 기본 Pydantic 모델 (LoginRequest)
│   │
│   ├── core/                     # 핵심 설정 및 구성
│   │   ├── settings.py           # 환경 설정 관리 (Settings 클래스)
│   │   ├── openai_config.py      # LLM 설정 (Azure OpenAI, Gemini, OpenAI)
│   │   ├── logging.py            # JSON 기반 로깅 설정
│   │   └── __init__.py
│   │
│   ├── middleware/               # HTTP 미들웨어
│   │   ├── request_context.py    # 요청 컨텍스트 (trace_id 관리)
│   │   └── __pycache__
│   │
│   ├── routes/                   # API 라우트/엔드포인트
│   │   ├── items.py              # 문제 목록, 저장, 수정, 조회
│   │   ├── generate.py           # 문제 생성 (스트리밍)
│   │   ├── generate_multi.py     # 다중 문제 생성
│   │   ├── generate_one.py       # 단일 문제 생성
│   │   ├── pages.py              # 페이지 관리 (CRUD)
│   │   ├── items_meta.py         # 문제 메타데이터
│   │   ├── suggest_types.py      # 문제 유형 추천
│   │   ├── export_docx.py        # Word 문서 내보내기
│   │   └── __init__.py
│   │
│   ├── schemas/                  # Pydantic 데이터 모델
│   │   ├── generate.py           # GenerateRequest (difficulty, topic)
│   │   ├── items_mcq.py          # MCQ 문항 스키마
│   │   ├── items_lc.py           # LC(Listening) 문항
│   │   ├── items_rc28.py         # RC28 특화 스키마
│   │   ├── items_rc_set.py       # RC 세트 문항
│   │   ├── export_docx.py        # 내보내기 페이로드
│   │   ├── error.py              # 에러 정의
│   │   └── __init__.py
│   │
│   ├── models/                   # 특화 모델들
│   │   ├── rc22.py               # RC22 모델
│   │   ├── rc31.py               # RC31 모델
│   │   └── rc40.py               # RC40 모델
│   │
│   ├── services/                 # 비즈니스 로직
│   │   ├── item_generator.py     # 문항 생성 (LLM 호출, 검증, 재시도)
│   │   ├── item_pipeline.py      # 문항 생성 파이프라인
│   │   ├── type_router.py        # 문항 유형 라우팅 (규칙 + LLM)
│   │   ├── llm_client.py         # LLM 클라이언트 (JSON 파싱, 에러 처리)
│   │   ├── routing_rules.py      # 규칙 기반 유형 추천 (RC18~RC45)
│   │   ├── docx_export.py        # Word 문서 생성 로직
│   │   ├── http_client.py        # HTTP 요청 헬퍼
│   │   ├── mock_java.py          # Java API 모킹
│   │   ├── postprocess.py        # 후처리 (HTML 등)
│   │   ├── validators.py         # 검증 로직
│   │   ├── image_adapters.py     # 이미지 처리
│   │   └── __init__.py
│   │
│   ├── prompts/                  # LLM 프롬프트 관리
│   │   ├── base.py               # 기본 시스템 프롬프트
│   │   ├── prompt_data.py        # 문항 유형별 프롬프트 (대형 파일)
│   │   ├── prompt_manager.py     # 프롬프트 로딩/관리
│   │   ├── router_prompt.py      # 라우팅 프롬프트
│   │   ├── type_mapping.py       # 문항 유형 매핑
│   │   ├── micro_topics.py       # 마이크로 토픽 관리
│   │   ├── items/                # 문항별 프롬프트들
│   │   │   ├── base.py
│   │   │   ├── lc01.py~lc17.py   # Listening Comprehension
│   │   │   ├── rc18.py~rc45.py   # Reading Comprehension
│   │   │   └── ...
│   │   └── __init__.py
│   │
│   ├── specs/                    # 문항 생성 스펙 (AI 로직)
│   │   ├── base.py               # ItemSpec 베이스 클래스
│   │   ├── registry.py           # 스펙 레지스트리 (RC18~RC45 매핑)
│   │   ├── auto_from_prompt_data.py # 자동 스펙 생성
│   │   ├── passage_preprocessor.py # 지문 전처리
│   │   ├── helpers.py            # 헬퍼 함수들
│   │   ├── utils.py              # JSON 처리 유틸
│   │   ├── generate_with_retry.py # 재시도 로직
│   │   ├── lc_standard.py        # LC 표준 스펙
│   │   ├── lc06_payment_amount.py # LC06 특화
│   │   ├── rc_generic_mcq.py     # RC 일반 MCQ
│   │   ├── rc_set.py             # RC 세트형
│   │   ├── rc18_purpose.py ~ rc45 # RC 유형별 스펙들
│   │   └── __init__.py
│   │
│   └── __init__.py
│
├── data/                         # 정적 데이터
│   ├── micro_topics.json         # 마이크로 토픽 데이터
│   ├── micro_topics.bak.json     # 백업
│   └── micro_topics20250913.json # 버전 관리
│
└── __pycache__/                  # Python 캐시
```

---

## 4. 아키텍처 패턴

### 프로젝트 타입
- **백엔드 REST API** (FastAPI)
- **AI/LLM 통합** (문제 자동 생성)
- **교육 기술** (EdTech)

### 아키텍처 패턴
1. **레이어드 아키텍처**
   - Routes (API) → Services (비즈니스 로직) → Schemas/Models (데이터)

2. **스펙 기반 생성 패턴**
   - 각 문항 유형(RC18~RC45, LC01~LC17)별 독립적인 Spec 클래스
   - Spec Registry에서 동적 로딩

3. **하이브리드 라우팅**
   - 규칙 기반 (Regex 패턴) + LLM 기반 (AI 판단)
   - 55% LLM, 45% 규칙 가중 병합

4. **파이프라인 아키텍처**
   - 입력 → 프롬프트 로딩 → LLM 호출 → JSON 파싱 → 검증 → 후처리 → 응답

---

## 5. 주요 진입점

### main.py
- FastAPI 애플리케이션 초기화
- 미들웨어 등록 (CORS, RequestContext)
- 라우터 포함
- 전역 예외 처리기
- 접근 로깅
- OpenAPI 커스터마이징

### auth.py
- Java 서버와의 연동 로그인
- Redis 세션 관리
- Bearer 토큰 검증
- 대시보드 엔드포인트

---

## 6. API 라우팅 구조

| 라우터 | 경로 | 메서드 | 기능 |
|--------|------|--------|------|
| auth | `/api/auth/login` | POST | 사용자 로그인 |
| auth | `/api/auth/dashboard` | GET | 인증된 사용자 대시보드 |
| items | `/items/list` | GET | 문제 목록 조회 |
| items | `/items/save` | POST | 문제 저장 (Java 연동) |
| items | `/items/update` | POST | 문제 수정 |
| items | `/items/detail` | GET | 문제 상세 조회 |
| generate | `/api/generate/stream` | POST | 스트리밍 생성 |
| generate | `/api/generate/json` | POST | JSON 응답 생성 |
| pages | `/api/pages/list` | GET | 페이지 목록 |
| pages | `/api/pages/add` | POST | 페이지 생성 |
| pages | `/api/pages/edit` | POST | 페이지 수정 |
| pages | `/api/pages/delete` | POST | 페이지 삭제 |
| pages | `/api/pages/detail` | GET | 페이지 상세 |
| export | `/api/pages/export_docx` | POST | Word 문서 내보내기 (레거시) |
| export | `/api/exports/docx` | POST | Word 문서 내보내기 (신규) |

---

## 7. 상태 관리

### Redis 기반 세션 관리
```python
# 저장 형식
r.setex(f"auth:{token}", TTL=86400, json.dumps(user_info))

# 조회
user_data = r.get(f"auth:{token}")
```

### 요청 컨텍스트 (middleware)
```python
request.state.trace_id        # 요청 추적 ID
request.state.req_id          # 요청 ID
request.state.idempotency_key # 멱등성 키
request.state.elapsed_ms      # 응답 시간
request.state.debug           # 디버그 모드
```

### 토큰 기반 인증
- Bearer 토큰 형식: UUID
- Authorization 헤더: `Bearer {token}`
- 토큰 검증: `token_required` 의존성 함수

---

## 8. 외부 API 연동

### Java 백엔드 연동 (점검학원)
```
JAVA_BASE = "https://api-chungbuk.connectenglish.kr:8442"

- /api/teacher/login/check       # 로그인 검증
- /api/questions/add             # 문제 저장
- /api/questions/list            # 문제 목록
- /api/questions/edit            # 문제 수정
- /api/questions/detail          # 문제 상세
- /api/pages/add, edit, delete   # 페이지 CRUD
- /api/pages/question/add, edit  # 페이지 문제 관리
```

### LLM API (AI 문제 생성)
1. **Azure OpenAI** (기본)
   - Deployment: gpt-4o
   - API Version: 2025-01-01-preview

2. **Gemini** (선택)
   - Model: gemini-2.5-flash
   - 폴백: gemini-2.5-pro

3. **OpenAI Public** (선택)
   - Model: gpt-4 (레거시)

---

## 9. 문제 생성 파이프라인

```
사용자 요청 (generate_request)
    ↓
문항 유형 라우팅 (type_router)
    ├─ 규칙 기반 추천 (routing_rules)
    ├─ LLM 라우팅 (llm_client)
    └─ 가중 병합 (55% LLM, 45% 규칙)
    ↓
스펙 로드 (registry.get_spec)
    ↓
프롬프트 생성 (prompt_manager)
    ├─ 기본 시스템 프롬프트 (base.py)
    ├─ 문항 유형별 프롬프트 (prompt_data.py)
    └─ 지문 전처리 (passage_preprocessor)
    ↓
LLM 호출 (llm_client.call_llm_json)
    ├─ 재시도 로직 (tenacity)
    ├─ 타임아웃 관리 (15초)
    └─ 에러 처리
    ↓
JSON 파싱 (item_generator)
    ├─ 코드펜스 제거
    ├─ 스마트 따옴표 정규화
    ├─ 제어문자 제거
    └─ 정답 기호 정규화 (①~⑤ → "1"~"5")
    ↓
Pydantic 검증 (schemas)
    ├─ MCQItem 검증
    └─ 유형별 스키마 검증
    ↓
후처리 (postprocess)
    ├─ HTML 정제
    └─ 콘텐츠 검증
    ↓
응답 반환 (JSON 또는 스트리밍)
```

### 스트리밍 응답 (generate.py)
```python
# NDJSON 포맷 (한 줄 = 하나의 JSON)
yield preamble (상태, trace_id, 타임스탬프)
while task.done():
    yield heartbeat (8초마다)
yield final_result (성공/실패)
```

---

## 10. 문항 유형별 구성

### Listening Comprehension (LC01~LC17)
- 단일 스펙: `LCStandardSpec`
- LC06은 특화: `LC06PaymentAmountSpec` (가격/금액 지문)

### Reading Comprehension (RC18~RC45)

| 유형 | 이름 | 특징 |
|------|------|------|
| RC18 | Purpose | 편지/요청 목적 판단 |
| RC19 | Emotion | 저자의 감정/태도 |
| RC20 | Argument | 주장/제안 |
| RC21 | Underlined Inference | 밑줄 표현 추론 |
| RC22 | Main Point | 주제/핵심 |
| RC23 | Topic | 이야기 주제 |
| RC24 | Title | 제목 선택 |
| RC25 | Graph/Info | 그래프/표 |
| RC26 | Connective Function | 연결어 기능 |
| RC27 | Irrelevant Sentence | 무관한 문장 |
| RC28 | Detail (T/F) | 세부 사항 (참/거짓) |
| RC29 | Grammar | 문법 |
| RC30 | Lexical Appropriateness | 어휘 적절성 |
| RC31 | Blank (Word) | 빈칸 (단어) |
| RC32 | Blank (Phrase) | 빈칸 (구) |
| RC33 | Blank (Clause) | 빈칸 (절) |
| RC34 | MCQ | 다지선다형 |
| RC35 | Insertion | 문장 삽입 |
| RC36 | Order (Easy) | 배열 (쉬움) |
| RC37 | Order (Hard) | 배열 (어려움) |
| RC38 | Insertion (Sentence) | 문장 삽입 (번호) |
| RC39 | Insertion (Paragraph) | 문단 삽입 |
| RC40 | Summary | 요약 |
| RC41~42 | Set | 문항 세트 |
| RC43~45 | Set | 문항 세트 |

---

## 11. 핵심 서비스 파일

### item_generator.py (문항 생성 핵심)
```python
def generate_item(item_id, payload, trace_id):
    # 1. 프롬프트 로드
    # 2. 재시도 루프 시작
    #    a) LLM 호출
    #    b) JSON 파싱 (pre_json_fix)
    #    c) Pydantic 검증
    #    d) 실패 시 재시도 (최대 2회)
    # 3. 후처리 및 반환
```

### type_router.py (문항 유형 자동 추천)
```python
def route_item_type(passage):
    # 1. 규칙 기반 후보 추출 (routing_rules)
    # 2. LLM 라우팅 (call_llm_json)
    # 3. 병합 및 정렬 (55% LLM, 45% 규칙)
    # 4. 길이 기반 필터링 (≤150: RC33까지, 151-199: RC40까지, ≥200: RC41+)
    return sorted_candidates
```

### llm_client.py (LLM 호출 및 파싱)
```python
def call_llm_json(messages, temperature=0.2, max_tokens=4000, timeout_s=30):
    # 1. 재시도 로직 (tenacity)
    # 2. LLM 호출 (Azure/Gemini/OpenAI)
    # 3. 응답 전처리:
    #    - 코드펜스 제거
    #    - 스마트 따옴표 정규화
    #    - 제어문자 제거
    #    - 정답 기호 정규화
    # 4. JSON 파싱 (느슨한 파싱)
    # 5. 최종 검증
    return json_object
```

### routing_rules.py (규칙 기반 추천)
```python
def rule_based_candidates(passage):
    # Regex 신호 분석:
    # - 밑줄 <u>...</u> → RC21, RC29, RC30
    # - 원형 숫자 ①~⑤ → RC29, RC30, RC38
    # - 괄호 삽입 (①)~(⑤) → RC38, RC39
    # - 문단 라벨 (A)(B)(C) → RC36, RC37
    # - 안내문 키워드 (Title:, Date:) → RC27, RC28
    # - 표/그래프 → RC25
    # - 전기 (born, awarded) → RC26 (연결어)
    # - 감정 단어 → RC19
    # - 주장 단어 (should, must) → RC20
    # - 문법 신호 → RC29, RC30

    return candidates_with_fit_scores
```

### docx_export.py (Word 문서 생성)
```python
def generate_docx(export_payload):
    # 1. 페이로드 파싱
    # 2. python-docx로 문서 생성
    # 3. 스타일 적용
    # 4. 문제 삽입
    # 5. 임시 파일 저장
    return tmp_path, filename
```

---

## 12. 환경 설정 (.env)

```env
# Java API 연동
JAVA_AUTH_URL=https://interface.smartreeglobal.com:8442/api/teacher/login/check
JAVA_BASIC_AUTH=Basic <base64_encoded>
JAVA_BASE=https://interface.smartreeglobal.com:8442
JAVA_SAVE_URL=https://api-chungbuk.connectenglish.kr:8442/api/questions/add
JAVA_LIST_URL=https://api-chungbuk.connectenglish.kr:8442/api/questions/list
JAVA_UPDATE_URL=https://api-chungbuk.connectenglish.kr:8442/api/questions/edit
JAVA_DETAIL_URL=https://api-chungbuk.connectenglish.kr:8442/api/questions/detail
JAVA_PAGES_BASIC_AUTH=Basic <base64_encoded>

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_TTL=86400 (24시간)

# LLM 설정
OPENAI_API_TYPE=azure (또는 gemini/openai)

# Azure OpenAI
AZURE_OPENAI_KEY=<key>
AZURE_OPENAI_ENDPOINT=https://aicsat.openai.azure.com/
AZURE_OPENAI_API_VERSION=2025-01-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o

# Gemini
GEMINI_API_KEY=<key>
GEMINI_MODEL_NAME=gemini-2.5-flash

# OpenAI Public
OPENAI_API_KEY=<key>
OPENAI_MODEL_NAME=gpt-4

# 서버 설정
CORS_ORIGINS=http://192.168.0.23:3000
JAVA_MOCK=1 (모드 테스트용)
APP_DEBUG=0
```

---

## 13. 로깅 시스템

### JSON 기반 구조화 로깅
```json
{
  "ts": "2025-12-29T15:30:45.123Z",
  "ts_ms": 1735419045123,
  "level": "INFO",
  "logger": "app.generate",
  "msg": "item_generated",
  "req_id": "550e8400-e29b-41d4-a716-446655440000",
  "trace_id": "...",
  "elapsed_ms": 2345,
  "path": "/api/generate/stream",
  "method": "POST",
  "status": 200
}
```

### 로그 채널
- uvicorn: 서버 로그
- uvicorn.access: HTTP 접근 로그
- uvicorn.error: 에러 로그
- app.*: 애플리케이션 로그

### 민감정보 레드액션
- Authorization 헤더 자동 마스킹
- `Authorization: Basic ***REDACTED***`

---

## 14. 미들웨어 구성

| 미들웨어 | 기능 |
|---------|------|
| RequestContextMiddleware | Trace ID 생성/관리 |
| CORSMiddleware | CORS 정책 (모든 오리진 허용) |
| HTTP 접근 로깅 | 모든 요청/응답 로깅 |
| 예외 처리기 | 전역 에러 핸들링 |

---

## 15. 주요 특징

### 1. AI 기반 문제 생성
- Azure OpenAI/Gemini와 실시간 통신
- 재시도 로직 (최대 2회)
- 타임아웃 관리 (15초)
- JSON 파싱 복원력 (스마트 따옴표 등)

### 2. 하이브리드 라우팅
- 규칙 기반 (정규식): 45%
- LLM 기반: 55%
- 길이별 필터링 (RC18~RC45 28개 유형)

### 3. 교육 특화
- CSAT (수능) 기준 영어 문제
- 문항 유형별 전문 스펙
- 마이크로 토픽 기반 주제 관리

### 4. 엔터프라이즈 기능
- 외부 Java 시스템 통합
- Redis 세션 관리
- 트레이싱 (trace_id)
- Word 문서 자동 생성

### 5. API 스트리밍
- 장시간 작업 대응 (하트비트)
- 타임아웃 방지
- NDJSON 포맷

---

## 16. 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────┐
│                  FastAPI 애플리케이션                    │
├─────────────────────────────────────────────────────────┤
│ Middleware: CORS, RequestContext, Exception Handler      │
├─────────────────────────────────────────────────────────┤
│  Routes Layer                                            │
│  ├─ /api/auth (로그인 + 세션)                          │
│  ├─ /items (문제 CRUD + Java 연동)                     │
│  ├─ /api/generate (AI 문제 생성)                       │
│  ├─ /api/pages (페이지 관리)                           │
│  └─ /api/exports (Word 문서)                           │
├─────────────────────────────────────────────────────────┤
│  Services Layer                                          │
│  ├─ item_generator.py (생성 주 로직)                   │
│  ├─ type_router.py (유형 추천)                         │
│  ├─ llm_client.py (LLM 통신)                           │
│  ├─ routing_rules.py (규칙 기반)                       │
│  └─ docx_export.py (문서 생성)                         │
├─────────────────────────────────────────────────────────┤
│  Core & Config Layer                                     │
│  ├─ settings.py (환경)                                  │
│  ├─ openai_config.py (LLM 설정)                        │
│  └─ logging.py (JSON 로그)                              │
├─────────────────────────────────────────────────────────┤
│  Prompts & Specs Layer                                   │
│  ├─ base.py (기본 프롬프트)                            │
│  ├─ prompt_data.py (문항별 프롬프트)                    │
│  └─ specs/ (RC18~RC45 생성 로직)                       │
├─────────────────────────────────────────────────────────┤
│  External Services                                       │
│  ├─ Azure OpenAI (LLM)                                  │
│  ├─ Gemini API (대체 LLM)                               │
│  ├─ Java Backend (문제 저장)                            │
│  └─ Redis (세션)                                        │
└─────────────────────────────────────────────────────────┘
```

---

## 17. 데이터 흐름 예시

### 문제 생성 요청
```json
POST /api/generate/stream

{
  "difficulty": "high",
  "topic": "환경 보전",
  "interest": "기본"
}

응답 (NDJSON):
{"itemId":"<uuid>","status":"stream","trace_id":"...","ts":...}
{"heartbeat":...}
{"heartbeat":...}
{"itemId":"<uuid>","status":"ok","data":{...}}
```

### 문제 저장 (Java 연동)
```json
POST /items/save

{
  "item_type": "RC32",
  "item_name": "빈칸 (구)",
  "difficulty": "high",
  "topic": "환경",
  "passage": "{...JSON...}"
}

응답:
{
  "message": "저장 성공",
  "question_seq": 12345
}
```

---

## 18. 현재 구현 상태

### 완전 구현
- 인증 (JWT + Redis)
- 문제 조회/저장/수정 (Java 연동)
- 문제 생성 (AI 기반)
- 페이지 관리 (CRUD)
- Word 문서 내보내기
- 스트리밍 응답

### 개발 중
- 이미지 처리 (image_adapters.py - 비어있음)
- 추가 문항 유형 스펙

### 테스트 모드
- JAVA_MOCK=1 환경 변수로 Java API 모킹 가능
