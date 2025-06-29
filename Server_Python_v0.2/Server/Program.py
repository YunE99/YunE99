import datetime
import socket
import threading
import time
import os
import asyncio
from dotenv import load_dotenv
# import ChatRoom, ClientSessionMgr
from Core.Listener import Listener
from Core.Helper import eDataType, eServerType, ServerInfo
from Server.Session.ClientSessionMgr import ClientSessionMgr


class Program:
    # Member Attributes
    load_dotenv()

    m_listener = Listener()
    # m_chatRoom = ChatRoom()

    @staticmethod
    async def main():
        # DNS
        dmHost = socket.gethostname()
        ipHost = socket.gethostbyname(dmHost)
        ipAddr = None

        # 서버 타입에 따른 IP 주소 설정
        now = datetime.datetime.now()
        time_str = now.strftime('%H:%M:%S') + f":{now.microsecond // 100:04d}"  # 마이크로초 6자리 → 앞 4자리만 사용

        if ServerInfo.SERVER_TYPE == eServerType.DEV:
            ipAddr = os.getenv("myipAddr1")
            print(f"[Program] <{time_str}> Activating DEV Server!!!")

        elif ServerInfo.SERVER_TYPE == eServerType.QA:
            ipAddr = os.getenv("myipAddr2")
            print(f"[Program] <{time_str}> Activating QA Server!!!")

        elif ServerInfo.SERVER_TYPE == eServerType.LIVE:
            ipAddr = os.getenv("myipAddr2")
            print(f"[Program] <{time_str}> Activating LIVE Server!!!")

        endPointServer = (ipAddr, ServerInfo.PORT_SERVER_IN)
        print(f"[Program] endPointServer : {endPointServer}")

        # 리스너 초기화
        await Program.m_listener.Init(endPointServer, ClientSessionMgr.instance().generate)

        # 무한 루프 실행
        while True:
            # Program.m_chatRoom.push(lambda: Program.m_chatRoom.flush())
            await asyncio.sleep(0.25)


if __name__ == "__main__":
    asyncio.run(Program.main())
