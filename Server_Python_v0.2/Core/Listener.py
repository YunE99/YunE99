import socket
import asyncio
from typing import Callable
from Core.Session.BaseSession import BaseSession

class Listener:  # Run on the Server
    def __init__(self):
        self.m_socketServer = None
        self.m_fcSessionFactory: Callable[[], 'BaseSession'] = None
        
    
    # @@@ 초기화 @@@
    async def Init(self, endPoint: tuple, m_fcSessionFactory: Callable[[], 'BaseSession'], register: int = 1, backlog: int = 100): #register: int = 10
        print(f"[Listener] endPoint : {endPoint[0]}")
        self.loop = asyncio.get_running_loop()

        self.m_socketServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.m_socketServer.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.m_socketServer.bind(endPoint)
        self.m_socketServer.listen(backlog)  # backlog : 최대 대기수
        self.m_socketServer.setblocking(False)  # 논블로킹 소켓 설정
        
        self.m_fcSessionFactory = m_fcSessionFactory
        
        for _ in range(register):
            asyncio.create_task(self.RegisterAccept())
        await asyncio.sleep(1)
    
    # @@@ 접속 요청 @@@
    async def RegisterAccept(self):
        while True:
            try:
                print("[Listener] 접속 요청 중")
                clientSocket, clientAddress = await self.loop.sock_accept(self.m_socketServer)
                # print(f"[Listener] {clientSocket}, {clientAddress}")
                print(f"[Listener] {clientAddress} 클라이언트 접속됨")
                
                asyncio.create_task(self.OnCompletedAccept(clientSocket, clientAddress))

            except Exception as e:
                print(f"[Listener] RegisterAccept Error {e}")
                await asyncio.sleep(0.1)

    # @@@ 접속 결과 @@@
    async def OnCompletedAccept(self, clientSocket, clientAddress):
        try:
            session = self.m_fcSessionFactory()
            print(f"[Listener] 생성된 세션 객체: {session}")  # ✅ 디버깅 추가
            print(f"[Listener] sessionStart 존재 여부: {hasattr(session, 'sessionStart')}")  # ✅ sessionStart 확인
            
            if callable(getattr(session, "sessionStart", None)):  # ✅ sessionStart가 메서드인지 확인
                await session.sessionStart(clientSocket)
            else:
                print("[Listener] sessionStart가 메서드가 아닙니다!")
                
            print(f"[Listener] sessionStart 호출 완료")  # ✅ sessionStart가 실행되는지 확인
            await session.OnConnected(clientAddress)
        except Exception as e:
            print(f"[Listener] OnCompletedAccept Fail {e}")
        
        asyncio.create_task(self.RegisterAccept())
