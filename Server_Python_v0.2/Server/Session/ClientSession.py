import datetime
import socket
from Core.Session.PacketSession import PacketSession
from Server.Packet.PacketMgrServer import PacketMgrServer
from Server.UserMgr.UserMgr import UserMgr



class ClientSession(PacketSession):

    def __init__(self):
        super().__init__()
        self.m_chatRoom = None
        self.m_sessionID = None


    # @@@ 접속 @@@
    async def OnConnected(self, endPoint: tuple):
        print("[ClientSession] <{0}> Connected Client {1} [ID : {2}]".format(
            datetime.datetime.now().strftime("%H:%M:%S:%f"), endPoint, self.m_sessionID
        ))

    # @@@ 해제 @@@
    async def OnDisconnected(self, endPoint: tuple):
        from Server.Session.ClientSessionMgr import ClientSessionMgr
        UserMgr.Instance().Logout(self)
        ClientSessionMgr.instance().removeSession(self)
        print("[ClientSession] <{0}> Disconnected Client {1} [ID : {2}]".format(
            datetime.datetime.now().strftime("%H:%M:%S:%f"), endPoint, self.m_sessionID
        ))

    # @@@ 수신 @@@
    def OnRecv(self, buffRecv: bytes):
        PacketMgrServer.g_instance().OnRecvPacket(self, buffRecv)

    # @@@ 송신 @@@
    def OnSend(self, numOfByte: int):
        # print("<{0}> [Send Client] SizeOfByte : {1} ".format(
        #    datetime.datetime.now().strftime("%H:%M:%S:%f"), numOfByte))
        pass

    # Getter & Setter
    @property
    def chatRoom(self):
        return self.m_chatRoom

    def setChatRoom(self, room):
        self.m_chatRoom = room

    @property
    def sessionID(self):
        return self.m_sessionID

    def setSessionID(self, id: int):
        self.m_sessionID = id  # 세션 ID 설정
