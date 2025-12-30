from fastapi import APIRouter, Request, HTTPException, Header, Depends, Query
from pydantic import BaseModel
from typing import List
import os, requests, json
from fastapi.responses import JSONResponse

router = APIRouter()

JAVA_SAVE_URL = os.getenv("JAVA_SAVE_URL")
JAVA_LIST_URL = os.getenv("JAVA_LIST_URL")
JAVA_UPDATE_URL= os.getenv("JAVA_UPDATE_URL")
JAVA_DETAIL_URL= os.getenv("JAVA_DETAIL_URL")
JAVA_BASIC_AUTH = os.getenv("JAVA_BASIC_AUTH")



import redis
r = redis.Redis(host='localhost', port=6379, db=0)

# ✅ 수신 데이터 구조
class ItemRequest(BaseModel):
    item_type: str         # 프론트에서 선택한 문항 유형
    item_name: str         # 프론트에서 선택한 버튼 라벨
    difficulty: str        # 'easy', 'medium', 'high'
    topic: str             # 주제
    passage: str           # 원시 JSON 통째로 저장

class ItemEditRequest(BaseModel):
    question_seq: int
    item_name: str
    difficulty: str
    topic: str
    passage: str
    item_type: str  # ← 프론트에서 보내는 키    

# ✅ 인증 확인 함수
def token_required(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="인증 토큰이 필요합니다")
    token = authorization.replace("Bearer ", "")
    user_data = r.get(f"auth:{token}")
    if not user_data:
        raise HTTPException(status_code=401, detail="토큰이 만료되었거나 유효하지 않습니다")
    return json.loads(user_data)

@router.get("/list")
def get_items_list(user=Depends(token_required),
    page: int = Query(1, ge=1),
    perPageNum: int = Query(14, ge=1, alias="perPageNum"),):
    try:
        payload = {
            "page": page,
            "page_size": perPageNum,
            "sch_user_seq": user["user_seq"],  # 로그인 사용자 ID
        }

        headers = {
            "Authorization": JAVA_BASIC_AUTH,
            "Content-Type": "application/json"
        }

        response = requests.post(
            JAVA_LIST_URL,
            json=payload,
            headers=headers,
            timeout=5,
            verify=False
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=500, detail="Java API 응답 오류")

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Java API 요청 실패: {str(e)}")
    
@router.post("/detail")
def get_item_detail(data: dict, token: dict = Depends(token_required)):
    
    try:
        payload = {
            "question_seq": data["question_seq"],
            "user_seq": token["user_seq"]  # ✅ 로그인한 사용자 ID 추가
        }
        
        response = requests.post(
            JAVA_DETAIL_URL,
            json=payload,
            headers={
                "Authorization": JAVA_BASIC_AUTH,
                "Content-Type": "application/json"
            },
            timeout=5,
            verify=False
        )
        print(" item/detail   ",payload)
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=500, detail="Java API 에러")

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Java 요청 실패: {str(e)}")

    
# ✅ 저장 엔드포인트
@router.post("/save")
def save_item(item: ItemRequest, user=Depends(token_required)):
    try:
        payload = {
            "user_seq": user["user_seq"],
            "difficulty": item.difficulty,
            "topic": item.topic,
            "question_type": item.item_type,
            "item_name": item.item_name,
            "passage": item.passage,         # 원시 JSON 전체 저장
            "question_text": "",             # 필수지만 의미 없으므로 빈값
            "transcript": "",
            "correct_answer": "",
            "explain": "",
            "options": []                    # 구조는 유지하되 빈 리스트
        }

        print("📤 Java API 전송 payload:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))

        response = requests.post(
            JAVA_SAVE_URL,
            json=payload,
            headers={
                "Authorization": JAVA_BASIC_AUTH,
                "Content-Type": "application/json"
            },
            timeout=5,
            verify=False
        )

        if response.status_code == 200:
            return {"message": "저장 성공", "java_response": response.json()}
        else:
            print("❌ Java 응답 상태코드:", response.status_code)
            raise HTTPException(status_code=500, detail="Java API 저장 실패")

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Java API 연결 실패: {str(e)}")

# ✅ 저장 엔드포인트
@router.post("/update")
def update_item(item: ItemEditRequest, user=Depends(token_required)):
    try:
        payload = {
            "user_seq": user["user_seq"],
            "question_seq": item.question_seq,   # ✅ 이제 모델에 존재
            "difficulty": item.difficulty,
            "topic": item.topic,
            "question_type": item.item_type,     # ✅ 프론트의 item_type → Java의 question_type
            "item_name": item.item_name,
            "passage": item.passage,             # 원시 JSON 전체 저장
            "question_text": "",                 # 필수지만 의미 없으므로 빈값
            "transcript": "",
            "correct_answer": "",
            "explain": "",
            "options": []
        }

        print("📤 Java API 전송 payload:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))

        response = requests.post(
            JAVA_UPDATE_URL,
            json=payload,
            headers={
                "Authorization": JAVA_BASIC_AUTH,
                "Content-Type": "application/json"
            },
            timeout=5,
            verify=False
        )

        if response.status_code == 200:
            # 프론트의 UpdateItemResponse<T>와 형식을 맞추면 후속 처리가 매끄럽습니다.
            return {
                "ok": True,
                "item": response.json(),   # 필요 시 가공
                "update_token": None
            }
        else:
            print("❌ Java 응답 상태코드:", response.status_code)
            raise HTTPException(status_code=500, detail="Java API 저장 실패")

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Java API 연결 실패: {str(e)}")