from fastapi import Request, Depends, HTTPException


def token_required(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="인증 토큰이 필요합니다")

    token = auth_header.replace("Bearer ", "")
    user_data = r.get(f"auth:{token}")
    if not user_data:
        raise HTTPException(status_code=401, detail="토큰이 만료되었거나 유효하지 않습니다")

    return json.loads(user_data)