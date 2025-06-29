import threading

class ServerInfo:
    TARGET_BUFFER_SIZE = 1024  # 실제 환경에 맞게 조정 필요

class SendBuffer:
    def __init__(self, chunkSize):
        self.chunkSize = chunkSize
        self.buffer = bytearray(chunkSize)
        self.offset = 0

    @property
    def NowRemainSize(self):
        return self.chunkSize - self.offset

    def Open(self, reserveSize):
        if self.NowRemainSize < reserveSize:
            return None  # C#에서 새로운 SendBuffer를 할당하는 방식과 유사하게 처리

        segment = memoryview(self.buffer)[self.offset:self.offset + reserveSize]
        self.offset += reserveSize
        return segment

    def Close(self, usedSize):
        return memoryview(self.buffer)[:usedSize]

class SendBufferMgr:
    CurBuffer = threading.local()
    ChunkSize = ServerInfo.TARGET_BUFFER_SIZE * 100

    @staticmethod
    def Open(reserveSize):
        if not hasattr(SendBufferMgr.CurBuffer, "Value") or SendBufferMgr.CurBuffer.Value is None:
            SendBufferMgr.CurBuffer.Value = SendBuffer(SendBufferMgr.ChunkSize)

        if SendBufferMgr.CurBuffer.Value.NowRemainSize < reserveSize:
            SendBufferMgr.CurBuffer.Value = SendBuffer(SendBufferMgr.ChunkSize)

        return SendBufferMgr.CurBuffer.Value.Open(reserveSize)

    @staticmethod
    def Close(usedSize):
        return SendBufferMgr.CurBuffer.Value.Close(usedSize)

    @staticmethod
    def Generate(*aBuffers):
        reserveSize = sum(len(buf) for buf in aBuffers)

        openSeg = SendBufferMgr.Open(reserveSize)
        if openSeg is None:
            return None  # 버퍼를 확보할 수 없는 경우

        curWrite = 0
        for nowBuffer in aBuffers:
            openSeg[curWrite:curWrite + len(nowBuffer)] = nowBuffer
            curWrite += len(nowBuffer)

        return SendBufferMgr.Close(curWrite)
