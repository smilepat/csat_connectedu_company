import os, uuid, json
import requests
import redis
from fastapi import APIRouter, HTTPException
from app.models import LoginRequest
from dotenv import load_dotenv
from fastapi import Request, Depends, status

load_dotenv()
router = APIRouter()

JAVA_API_URL = os.getenv("JAVA_AUTH_URL")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_TTL = int(os.getenv("REDIS_TTL", 86400))  # 30분

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

@router.post("/login")
def login(request: LoginRequest):
    print("✅ /api/auth/login 요청 도착")
    try:
        res = requests.post(JAVA_API_URL, json=request.dict(), timeout=5)
        data = res.json()

        print("응답 데이터:", data)

        if "coach_info" not in data:
            raise HTTPException(status_code=500, detail="Java 응답에 coach_info가 없습니다")

        user_info = data["coach_info"]

        token = str(uuid.uuid4())
        r.setex(f"auth:{token}", REDIS_TTL, json.dumps(user_info))

        return {
            "message": "로그인 성공",
            "token": token,
            "user": user_info
        }

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Java 서버 연결 실패: {str(e)}")
    

AUTH_MESSAGE = "세션이 만료되었습니다. 다시 로그인하세요."

def token_required(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        # 토큰 없음
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": AUTH_MESSAGE,
                "code": "AUTH_REQUIRED",
                "login_url": "/login"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = auth_header.replace("Bearer ", "", 1).strip()

    try:
        user_data = r.get(f"auth:{token}")
    except Exception:
        # Redis 연결/오류
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="세션 저장소 오류가 발생했습니다."
        )

    if not user_data:
        # 토큰 만료/무효
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": AUTH_MESSAGE,
                "code": "AUTH_EXPIRED",
                "login_url": "/login"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        user_json = json.loads(user_data)
        if not isinstance(user_json, dict):
            raise ValueError("Invalid session payload")
        return user_json
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": AUTH_MESSAGE,
                "code": "AUTH_CORRUPT",
                "login_url": "/login"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )

@router.get("/dashboard")
def dashboard(user=Depends(token_required)):
    return {
        "message": f"{user['name']}님 환영합니다",
        "coaching_date": user["coaching_date"]
    }
