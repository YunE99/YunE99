import asyncio
import socket
from abc import ABC, abstractmethod
from collections import deque
from Core.ReceiveBuffer import ReceiveBuffer
from Core.Helper import ServerInfo

class BaseSession(ABC):
    def __init__(self):
        self.m_socket = None
        self.m_flagDisconn = 0
        self.m_lock = asyncio.Lock()

        # 수신 관련
        self.m_recvBuff = ReceiveBuffer(ServerInfo.TARGET_BUFFER_SIZE)
        
        # 송신 관련
        self.m_sendQueue = deque()
        self.m_sendList = []

    async def clear(self):
        async with self.m_lock:
            self.m_sendQueue.clear()
            self.m_sendList.clear()

    async def sessionStart(self, socketClient):
        self.m_socket = socketClient
        print(f"[BaseSession] 세션 시작 {self.m_socket}")
        asyncio.create_task(self.recvRegister())
        return self

    async def sessionDisConnect(self):
        if self.m_flagDisconn == 1:
            return
        
        self.m_flagDisconn = 1
        await self.OnDisconnected(self.m_socket.getpeername())
        self.m_socket.shutdown(socket.SHUT_RDWR)
        self.m_socket.close()
        await self.clear()

    async def recvRegister(self):
        if self.m_flagDisconn == 1:
            return
        
        self.m_recvBuff.Clear()
        try:
            data = await asyncio.get_running_loop().sock_recv(self.m_socket, ServerInfo.TARGET_BUFFER_SIZE)
            await self.onRecvComplete(data)
        except Exception as e:
            print(f"[BaseSession] recvRegister Error {e}")
            await self.sessionDisConnect()

    async def onRecvComplete(self, data):
        if data:
            try:
                if not self.m_recvBuff.WriteTryTransIndex(len(data)):
                    await self.sessionDisConnect()
                    return
                
                processLength = await self.OnRecv(data, 0)
                if processLength < 0 or self.m_recvBuff.NowDataSize < processLength:
                    await self.sessionDisConnect()
                    return
                
                if not self.m_recvBuff.ReadTryTransIndex(processLength):
                    await self.sessionDisConnect()
                    return
                
                await self.recvRegister()
            except Exception as e:
                print(f"[BaseSession] onRecvComplete Error {e}")
        else:
            print("[BaseSession] onRecvComplete Fail: 클라이언트가 연결을 종료했을 가능성")
            await self.sessionDisConnect()

    async def send(self, buffSend):
        async with self.m_lock:
            self.m_sendQueue.append(buffSend)
            if not self.m_sendList:
                await self.sendRegister()

    async def sendMultiple(self, liBuffSends):
        if not liBuffSends:
            return
        async with self.m_lock:
            self.m_sendQueue.extend(liBuffSends)
            if not self.m_sendList:
                await self.sendRegister()

    async def sendRegister(self):
        if self.m_flagDisconn == 1:
            return

        while self.m_sendQueue:
            self.m_sendList.append(self.m_sendQueue.popleft())

        try:
            for data in self.m_sendList:
                await asyncio.get_running_loop().sock_sendall(self.m_socket, data)
            await self.onSendComplete()
        except Exception as e:
            print(f"[BaseSession] sendRegister Error {e}")
            await self.sessionDisConnect()

    async def onSendComplete(self):
        async with self.m_lock:
            self.m_sendList.clear()
            await self.onSend(sum(len(data) for data in self.m_sendList))
            if self.m_sendQueue:
                await self.sendRegister()
            
    @abstractmethod
    async def OnConnected(self, endPoint):
        pass

    @abstractmethod
    async def OnRecv(self, buffRecv, t):
        pass

    @abstractmethod
    async def OnSend(self, numOfByte):
        pass

    @abstractmethod
    async def OnDisconnected(self, endPoint):
        pass