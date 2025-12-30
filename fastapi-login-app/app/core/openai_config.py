# app/core/openai_config.py
import os
import logging

log = logging.getLogger("core.openai")

OPENAI_API_TYPE = os.getenv("OPENAI_API_TYPE", "openai").lower()

# 공통 기본값
DEFAULT_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
DEFAULT_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4000"))

def _norm(s: str | None) -> str:
    return (s or "").strip()

# 통일된 시그니처:
# chat_completion(messages, *, trace_id=None, temperature=None, max_tokens=None, timeout_s=None) -> str
# - timeout_s(초): 있으면 SDK가 지원하는 범위에서 적용
# - trace_id: 지원되는 SDK(OpenAI v1 계열)에서는 X-Request-Id 헤더로 전달
if OPENAI_API_TYPE == "azure":
    # OpenAI Python SDK v1 계열 (Azure)
    from openai import AzureOpenAI

    client = AzureOpenAI(
        api_key=_norm(os.getenv("AZURE_OPENAI_KEY")),
        api_version=_norm(os.getenv("AZURE_OPENAI_API_VERSION", "2023-07-01-preview")),
        azure_endpoint=_norm(os.getenv("AZURE_OPENAI_ENDPOINT")),
    )

    def get_chat_model():
        return _norm(os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME") or os.getenv("AZURE_OPENAI_DEPLOYMENT") or "gpt-4o")

    def chat_completion(
        messages: list[dict],
        *,
        trace_id: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout_s: float | None = None,
    ) -> str:
        # per-call 옵션 주입
        opts = {}
        if timeout_s is not None:
            opts["timeout"] = timeout_s
        if trace_id:
            opts["extra_headers"] = {"X-Request-Id": trace_id}

        c = client.with_options(**opts) if opts else client
        

        resp = c.chat.completions.create(
            model=get_chat_model(),
            messages=messages,
            temperature=temperature if temperature is not None else DEFAULT_TEMPERATURE,
            max_tokens=max_tokens if max_tokens is not None else DEFAULT_MAX_TOKENS,
        )
        content = (resp.choices[0].message.content or "").strip() if resp.choices else ""
        return content

elif OPENAI_API_TYPE == "gemini":
    # Google Generative AI (Gemini)
    import google.generativeai as genai

    genai.configure(api_key=_norm(os.getenv("GEMINI_API_KEY")))

    def get_chat_model():

        # 환경 변수 GEMINI_MODEL_NAME에 올바른 값을 설정해주세요.
        return _norm(os.getenv("GEMINI_MODEL_NAME") or "gemini-2.5-pro")

    def chat_completion(
        messages: list[dict],
        *,
        trace_id: str | None = None,      # 헤더 주입은 공식 지원 X → 로깅으로만 활용
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout_s: float | None = None,   # 서비스 레이어에서 타임아웃 걸리므로 여기서는 참고만
    ) -> str:
        try:
            model = genai.GenerativeModel(get_chat_model())

            # [수정됨] OpenAI 형식의 메시지를 Gemini 형식으로 변환합니다.
            # 1. 'assistant' 역할을 'model' 역할로 변경합니다.
            # 2. 대화 목록을 문자열로 합치지 않고, 구조화된 리스트로 전달합니다.
            gemini_messages = [
                {'role': 'model' if m['role'] == 'assistant' else 'user', 'parts': [m['content']]}
                for m in messages
            ]

            # python 라이브러리의 per-request timeout 설정은 버전별로 상이 → 바깥 레이어에서 관리
            response = model.generate_content(
                gemini_messages,  # [수정됨] 구조화된 메시지 리스트를 그대로 전달
                generation_config={
                    "temperature": temperature if temperature is not None else DEFAULT_TEMPERATURE,
                    "max_output_tokens": max_tokens if max_tokens is not None else DEFAULT_MAX_TOKENS,
                },
            )
            # 우선순위: response.text → candidates 구조 (기존 로직 유지)
            if hasattr(response, "text") and response.text:
                return response.text.strip()
            if hasattr(response, "candidates") and response.candidates:
                parts = response.candidates[0].content.parts
                if parts and hasattr(parts[0], "text"):
                    return (parts[0].text or "").strip()
            raise ValueError("Gemini 응답에서 텍스트를 찾을 수 없습니다.")
        except Exception as e:
            # 빈 문자열 대신 예외를 던져 상위 레이어 재시도/로깅 활용
            log.warning("gemini_call_failed", extra={"trace_id": trace_id, "error": str(e)})
            raise

else:
    # OpenAI Public (레거시 0.x 스타일을 계속 쓰는 경우)
    # 권장: 최신 OpenAI Python(v1)로 마이그레이션하여 client.chat.completions.create 사용
    import openai
    openai.api_type = "openai"
    openai.api_key = _norm(os.getenv("OPENAI_API_KEY"))

    def get_chat_model():
        return _norm(os.getenv("OPENAI_MODEL_NAME") or "gpt-4")

    def chat_completion(
        messages: list[dict],
        *,
        trace_id: str | None = None,           # 0.x SDK는 extra_headers 미지원 → 헤더 전파 생략
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout_s: float | None = None,        # 0.x는 request_timeout 인자로 일부 지원
    ) -> str:
        kwargs = dict(
            model=get_chat_model(),
            messages=messages,
            temperature=temperature if temperature is not None else DEFAULT_TEMPERATURE,
            max_tokens=max_tokens if max_tokens is not None else min(DEFAULT_MAX_TOKENS, 1000),
        )
        if timeout_s is not None:
            kwargs["request_timeout"] = timeout_s  # openai==0.x 계열

        resp = openai.ChatCompletion.create(**kwargs)
        content = (resp.choices[0].message.content or "").strip() if resp.choices else ""
        return content
