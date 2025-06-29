class SendBuffer:
    # Member Attributes
    def __init__(self, chunkSize: int):

        self.m_buffer = bytearray(chunkSize)  # 버퍼
        self.m_idxWrite = 0  # 현재 쓰기 시작 인덱스

    # Member Methods
    def Open(self, reserveSize: int):

        if self.NowRemainSize < reserveSize:
            return None  # 남은 공간이 부족하면 None 반환
        return memoryview(self.m_buffer)[self.m_idxWrite:self.m_idxWrite + reserveSize]
    
    def Close(self, usedSize: int):
        segment = memoryview(self.m_buffer)[self.m_idxWrite + usedSize]
        self.m_idxWrite += usedSize
        return segment
    
    @property
    def NowRemainSize(self) -> int:
        return len(self.m_buffer) - self.m_idxWrite
    
    @property
    def IndexWrite(self) -> int:
        return self.m_idxWrite
    

    
    
