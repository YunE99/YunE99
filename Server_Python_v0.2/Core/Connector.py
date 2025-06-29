import socket
import asyncio
from typing import Callable
from Core.Session.BaseSession import BaseSession

class Connector:  # Run on the Client
    def __init__(self):
        self.m_fcGetSession: Callable[[], BaseSession] = None

    # 초기화
    async def connect(self, endPoint, fcGetSession, cnt=1):
        self.m_fcGetSession = fcGetSession

        for _ in range(cnt):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setblocking(False)

        try:
            # ✅ endPoint가 튜플이면 첫 번째 값만 사용
            if isinstance(endPoint, tuple):
                print(f"[INFO] endPoint 튜플 감지: {endPoint}, 첫 번째 값({endPoint[0]})을 사용합니다.")
                endPoint = endPoint[0]  # 첫 번째 값만 사용
        except Exception as e:
            print(f"[OnCompletedConnect Fail] {str(e)}")

    # 접속 요청
    async def connRegister(self, sock, endPoint):
        loop = asyncio.get_running_loop()
        try:
            await loop.sock_connect(sock, endPoint)
            await self.onConnComplete(sock, endPoint)
        except Exception as e:
            print(f"[OnCompletedConnect Fail] {str(e)}")

    # 접속 결과
    async def onConnComplete(self, sock, endPoint):
        try:
            if self.m_fcGetSession:
                session = self.m_fcGetSession()
                await session.SessionStart(sock)
                await session.OnConnected(endPoint)
        except Exception as e:
            print(f"[OnCompletedConnect Fail] {str(e)}")

