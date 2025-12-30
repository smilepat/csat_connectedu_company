# app/core/logging.py
import logging
import json
import sys
import re
from datetime import datetime, timezone
from typing import Any, Dict

logger = logging.getLogger("app")   # ✅ 전역 logger 등록
logger.setLevel(logging.INFO)
# --- 민감정보 레드액션(옵션) ---
REDACT_PATTERNS = [
    re.compile(r"(Authorization:\s*)(Basic|Bearer)\s+[A-Za-z0-9\-\._~\+\/]+=*", re.IGNORECASE),
]

def _redact(text: str) -> str:
    if not isinstance(text, str):
        return text
    out = text
    for pat in REDACT_PATTERNS:
        out = pat.sub(r"\1***REDACTED***", out)
    return out

SAFE_ATTR_BLOCKLIST = {
    "args","asctime","created","exc_info","exc_text","filename",
    "funcName","levelname","levelno","lineno","module","msecs",
    "message","msg","name","pathname","process","processName",
    "relativeCreated","stack_info","thread","threadName",
}

class JsonFormatter(logging.Formatter):
    """
    표준 JSON 로그 포맷:
    {
      "ts": "2025-10-24T01:23:45.678Z",
      "ts_ms": 1698101025678,
      "level": "INFO",
      "logger": "uvicorn.access",
      "msg": "pages_compose",
      "req_id": "...",
      "elapsed_ms": 123,
      "path": "/api/pages/compose",
      "method": "POST",
      "status": 200,
      ... (extra)
    }
    """
    def format(self, record: logging.LogRecord) -> str:
        # 타임스탬프
        now = datetime.now(timezone.utc)
        payload: Dict[str, Any] = {
            "ts": now.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "ts_ms": int(now.timestamp() * 1000),
            "level": record.levelname,
            "logger": record.name,
        }

        # 메시지와 레드액션
        msg = record.getMessage()
        payload["msg"] = _redact(msg)

        # extra 필드
        for k, v in record.__dict__.items():
            if k in SAFE_ATTR_BLOCKLIST:
                continue
            # req_id/trace_id 등은 표준 키로
            if k == "trace_id" and "req_id" not in payload:
                payload["req_id"] = v
            else:
                payload[k] = v

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        # 직렬화 안전장치
        try:
            return json.dumps(payload, ensure_ascii=False, default=str)
        except TypeError:
            # 혹시 모르는 비직렬화 객체 방지
            safe = {k: (str(v) if not isinstance(v, (str, int, float, bool, type(None), dict, list)) else v)
                    for k, v in payload.items()}
            return json.dumps(safe, ensure_ascii=False)

def configure_logging(level: str = "INFO") -> None:
    """
    - 루트/uvicorn 로거를 모두 JSON 포맷으로 교체
    - 콘솔(stdout) 출력
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())

    # uvicorn 기본 로거들(JSON으로 통일)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.addHandler(handler)
        # access 로거는 너무 시끄러우면 INFO/ERROR만 두고, 필요시 DEBUG로 상향
        lg.setLevel(level.upper())

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

# 편의 함수: 액션 로깅(라우터/서비스에서 호출)
def log_action(logger, req_id, user_seq, page_id, action, elapsed_ms, result, error=None):
    logger.info(
        f"[PAGE] req_id={req_id} user_seq={user_seq} page_id={page_id} "
        f"action={action} result={result} elapsed={elapsed_ms}ms error={error}"
    )
