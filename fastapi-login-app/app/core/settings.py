"""
환경 설정 모듈
환경별 설정을 관리하고 유효성 검증 수행
"""
import os
from typing import Optional, List
from functools import cached_property

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class BaseConfig(BaseSettings):
    """
    기본 설정 클래스
    모든 환경에서 공통으로 사용되는 설정
    """
    # ===========================================
    # 애플리케이션 설정
    # ===========================================
    SERVICE_NAME: str = Field(default="connectedu-itemgen")
    ENV: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")
    DEBUG: bool = Field(default=False)

    # ===========================================
    # 네트워크 설정
    # ===========================================
    REQUEST_TIMEOUT_MS: int = Field(default=15000)
    GENERATE_MAX_RETRIES: int = Field(default=2)
    RETRY_BACKOFF_MS: int = Field(default=500)

    # ===========================================
    # Redis 설정
    # ===========================================
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_DB: int = Field(default=0)
    REDIS_TTL: int = Field(default=86400)  # 24시간
    REDIS_URL: Optional[str] = None

    # ===========================================
    # Java API 설정
    # ===========================================
    JAVA_AUTH_URL: Optional[str] = None
    JAVA_BASE: Optional[str] = None
    JAVA_API_BASE_URL: Optional[str] = None
    JAVA_SAVE_URL: Optional[str] = None
    JAVA_LIST_URL: Optional[str] = None
    JAVA_UPDATE_URL: Optional[str] = None
    JAVA_DETAIL_URL: Optional[str] = None
    JAVA_BASIC_AUTH: Optional[str] = None
    JAVA_PAGES_BASIC_AUTH: Optional[str] = None
    JAVA_MOCK: bool = Field(default=False)

    # ===========================================
    # LLM API 설정
    # ===========================================
    OPENAI_API_TYPE: str = Field(default="azure")  # azure, gemini, openai

    # Azure OpenAI
    AZURE_OPENAI_KEY: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_API_VERSION: str = Field(default="2025-01-01-preview")
    AZURE_OPENAI_DEPLOYMENT: Optional[str] = None
    AZURE_OPENAI_DEPLOYMENT_NAME: Optional[str] = None

    # Gemini
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL_NAME: str = Field(default="gemini-2.5-flash")

    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL_NAME: str = Field(default="gpt-4")

    # ===========================================
    # CORS 설정
    # ===========================================
    CORS_ORIGINS: str = Field(default="http://localhost:3000")

    # ===========================================
    # 보안 설정
    # ===========================================
    SECRET_KEY: str = Field(default="change-me-in-production-use-strong-key")

    # ===========================================
    # 캐시 설정
    # ===========================================
    CACHE_TTL: int = Field(default=3600)  # 1시간
    CACHE_ENABLED: bool = Field(default=True)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v_upper

    @field_validator("OPENAI_API_TYPE")
    @classmethod
    def validate_api_type(cls, v: str) -> str:
        valid_types = ["azure", "gemini", "openai"]
        v_lower = v.lower()
        if v_lower not in valid_types:
            raise ValueError(f"OPENAI_API_TYPE must be one of {valid_types}")
        return v_lower

    @cached_property
    def cors_origins_list(self) -> List[str]:
        """CORS origins를 리스트로 반환"""
        if not self.CORS_ORIGINS:
            return []
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @cached_property
    def is_development(self) -> bool:
        """개발 환경 여부"""
        return self.ENV.lower() in ("dev", "development", "local")

    @cached_property
    def is_production(self) -> bool:
        """운영 환경 여부"""
        return self.ENV.lower() in ("prod", "production")

    @cached_property
    def redis_connection_url(self) -> str:
        """Redis 연결 URL"""
        if self.REDIS_URL:
            return self.REDIS_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


class DevelopmentConfig(BaseConfig):
    """개발 환경 설정"""
    ENV: str = Field(default="development")
    DEBUG: bool = Field(default=True)
    LOG_LEVEL: str = Field(default="DEBUG")


class StagingConfig(BaseConfig):
    """스테이징 환경 설정"""
    ENV: str = Field(default="staging")
    DEBUG: bool = Field(default=False)
    LOG_LEVEL: str = Field(default="INFO")


class ProductionConfig(BaseConfig):
    """운영 환경 설정"""
    ENV: str = Field(default="production")
    DEBUG: bool = Field(default=False)
    LOG_LEVEL: str = Field(default="WARNING")


class TestConfig(BaseConfig):
    """테스트 환경 설정"""
    ENV: str = Field(default="test")
    DEBUG: bool = Field(default=True)
    LOG_LEVEL: str = Field(default="DEBUG")
    REDIS_HOST: str = Field(default="localhost")
    REDIS_DB: int = Field(default=1)  # 테스트용 별도 DB


def get_settings() -> BaseConfig:
    """
    환경에 맞는 설정 객체 반환

    ENV 환경변수에 따라 적절한 설정 클래스를 선택
    """
    env = os.getenv("ENV", "development").lower()

    config_map = {
        "development": DevelopmentConfig,
        "dev": DevelopmentConfig,
        "local": DevelopmentConfig,
        "staging": StagingConfig,
        "stage": StagingConfig,
        "production": ProductionConfig,
        "prod": ProductionConfig,
        "test": TestConfig,
        "testing": TestConfig,
    }

    config_class = config_map.get(env, DevelopmentConfig)
    return config_class()


# 전역 설정 인스턴스
settings = get_settings()


# ===========================================
# 설정 검증 함수
# ===========================================

def validate_required_settings() -> List[str]:
    """
    필수 설정이 모두 있는지 검증

    Returns:
        누락된 설정 목록
    """
    missing = []

    # 운영 환경에서 필수인 설정들
    if settings.is_production:
        required = [
            ("SECRET_KEY", settings.SECRET_KEY != "change-me-in-production-use-strong-key"),
            ("JAVA_AUTH_URL", settings.JAVA_AUTH_URL),
            ("JAVA_BASIC_AUTH", settings.JAVA_BASIC_AUTH),
        ]

        for name, value in required:
            if not value:
                missing.append(name)

    # LLM API 설정 검증
    if settings.OPENAI_API_TYPE == "azure":
        if not settings.AZURE_OPENAI_KEY:
            missing.append("AZURE_OPENAI_KEY")
        if not settings.AZURE_OPENAI_ENDPOINT:
            missing.append("AZURE_OPENAI_ENDPOINT")
    elif settings.OPENAI_API_TYPE == "gemini":
        if not settings.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")
    elif settings.OPENAI_API_TYPE == "openai":
        if not settings.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")

    return missing


def print_settings_summary():
    """설정 요약 출력 (민감 정보 제외)"""
    print(f"""
    ========================================
    ConnectedU ItemGen API - Settings
    ========================================
    Environment: {settings.ENV}
    Debug: {settings.DEBUG}
    Log Level: {settings.LOG_LEVEL}
    Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}
    LLM Provider: {settings.OPENAI_API_TYPE}
    CORS Origins: {settings.cors_origins_list}
    ========================================
    """)
