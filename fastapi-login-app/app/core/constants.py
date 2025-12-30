"""
상수 정의 모듈
매직 스트링을 상수로 관리하여 유지보수성 향상
"""


class RedisKeys:
    """Redis 키 패턴 상수"""
    AUTH_SESSION = "auth:{token}"
    USER_PROFILE = "profile:{user_id}"
    CACHE_PREFIX = "cache:"

    @classmethod
    def auth_session(cls, token: str) -> str:
        return cls.AUTH_SESSION.format(token=token)

    @classmethod
    def user_profile(cls, user_id: int) -> str:
        return cls.USER_PROFILE.format(user_id=user_id)


class APIFields:
    """외부 API 응답 필드명"""
    COACH_INFO = "coach_info"
    USER_SEQ = "user_seq"
    COACHING_DATE = "coaching_date"
    NAME = "name"
    ROLE = "role"


class AuthCodes:
    """인증 관련 코드"""
    AUTH_REQUIRED = "AUTH_REQUIRED"
    AUTH_EXPIRED = "AUTH_EXPIRED"
    AUTH_CORRUPT = "AUTH_CORRUPT"
    AUTH_INVALID = "AUTH_INVALID"


class ErrorCodes:
    """에러 코드"""
    VALIDATION_FAILED = "VALIDATION_FAILED"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    ITEM_NOT_FOUND = "ITEM_NOT_FOUND"
    PAGE_NOT_FOUND = "PAGE_NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    REDIS_ERROR = "REDIS_ERROR"
    JAVA_API_ERROR = "JAVA_API_ERROR"


class ErrorMessages:
    """사용자 친화적 에러 메시지"""
    AUTH_REQUIRED = "로그인이 필요합니다."
    AUTH_EXPIRED = "세션이 만료되었습니다. 다시 로그인하세요."
    AUTH_INVALID = "유효하지 않은 인증 정보입니다."
    INVALID_INPUT = "입력값이 올바르지 않습니다."
    ITEM_NOT_FOUND = "요청한 문항을 찾을 수 없습니다."
    PAGE_NOT_FOUND = "요청한 페이지를 찾을 수 없습니다."
    ITEM_SAVE_FAILED = "문항 저장에 실패했습니다. 잠시 후 다시 시도하세요."
    API_UNAVAILABLE = "현재 서비스를 이용할 수 없습니다. 잠시 후 다시 시도하세요."
    INTERNAL_ERROR = "서버 오류가 발생했습니다. 관리자에게 문의하세요."
    REDIS_ERROR = "세션 저장소 오류가 발생했습니다."


class ItemTypes:
    """문항 유형"""
    # Listening Comprehension
    LC_TYPES = [f"LC{str(i).zfill(2)}" for i in range(1, 18)]

    # Reading Comprehension
    RC_TYPES = [f"RC{i}" for i in range(18, 46)]

    # All types
    ALL_TYPES = LC_TYPES + RC_TYPES


class DifficultyLevels:
    """난이도 레벨"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

    ALL = [EASY, MEDIUM, HARD]


class PageStatus:
    """페이지 상태"""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

    ALL = [DRAFT, PUBLISHED, ARCHIVED]


class HTTPHeaders:
    """HTTP 헤더 상수"""
    AUTHORIZATION = "Authorization"
    CONTENT_TYPE = "Content-Type"
    BEARER_PREFIX = "Bearer "
    BASIC_PREFIX = "Basic "
    JSON_CONTENT = "application/json"


class Timeouts:
    """타임아웃 설정 (초)"""
    JAVA_API = 5
    JAVA_API_LONG = 8
    LLM_API = 30
    REDIS = 3
