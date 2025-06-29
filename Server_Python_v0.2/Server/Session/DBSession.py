from Core.Session import PacketSession
import asyncio
import datetime
from Core import PacketSession
from Server import DBSessionMgr, PacketMgrServer

class DBSession(PacketSession):
    # 접속
    async def onConnected(self, endPoint):
        print("<{}> [Connected DB] {}".format(datetime.datetime.now().strftime("%H:%M:%S:%f"), endPoint))

    # 해제
    async def onDisconnected(self, endPoint):
        DBSessionMgr.Instance().remove(self)
        print("<{}> [Disconnected DB] {}".format(datetime.datetime.now().strftime("%H:%M:%S:%f"), endPoint))

    # 수신
    async def onRecv(self, buffRecv):
        await PacketMgrServer.Instance().onRecvPacket(self, buffRecv)

    # 송신
    async def onSend(self, numOfByte):
        pass  # 필요하면 구현
        