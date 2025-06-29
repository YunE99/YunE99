from fastapi import FastAPI, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import requests
import os
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# 카카오 API 정보
KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI")
KAKAO_AUTH_URL = "https://kauth.kakao.com/oauth/authorize"
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_USER_URL = "https://kapi.kakao.com/v2/user/me"

@app.get("/")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/auth/kakao")
async def kakao_callback():
    """ 카카오 로그인 URL로 리다이렉트 """
    kakao_login_url = (
        f"{KAKAO_AUTH_URL}?client_id={KAKAO_CLIENT_ID}"
        f"&redirect_uri={KAKAO_REDIRECT_URI}&response_type=code"
    )
    return RedirectResponse(kakao_login_url)

@app.get("/auth/callback")
async def kakao_callback(code: str):
    """ 카카오 인증 후 콜백 처리 """
    data = {
        "grant_type": "authorization_code",
        "client_id": KAKAO_CLIENT_ID,
        "redirect_uri": KAKAO_REDIRECT_URI,
        "code": code,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    # 액세스 토큰 요청
    response = requests.post(KAKAO_TOKEN_URL, data=data, headers=headers)
    token_json = response.json()
    access_token = token_json.get("access_token")

    if not access_token:
        return {"error": "Failed to get access token"}

    # 사용자 정보 요청
    headers = {"Authorization": f"Bearer {access_token}"}
    user_response = requests.get(KAKAO_USER_URL, headers=headers)
    user_info = user_response.json()

    kakao_id = user_info.get("id")
    kakao_nickname = user_info.get("kakao_account", {}).get("profile", {}).get("nickname")

    return templates.TemplateResponse("welcome.html", {"request": {}, "nickname": kakao_nickname})
if __name__ == "__main__":
    app.run()
