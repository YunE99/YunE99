class ReceiveBuffer:
    def __init__(self, bufferSize):
        self.m_buffer = bytearray(bufferSize)  # 버퍼
        self.m_idxRead = 0  # 현재 읽기 시작 인덱스
        self.m_idxWrite = 0  # 현재 쓰기 시작 인덱스

    # 클리어
    def Clear(self):
        dataSize = self.NowDataSize
        if dataSize == 0:
            self.m_idxRead = self.m_idxWrite = 0
        else:
            self.m_buffer[:dataSize] = self.m_buffer[self.m_idxRead:self.m_idxRead + dataSize]
            self.m_idxRead = 0
            self.m_idxWrite = dataSize

    # 현재 읽기 시작 인덱스 이동
    def ReadTryTransIndex(self, numOfBytes):
        if numOfBytes > self.NowDataSize:
            return False
        self.m_idxRead += numOfBytes
        return True

    # 현재 쓰기 시작 인덱스 이동
    def WriteTryTransIndex(self, numOfBytes):
        if self.NowRemainSize < numOfBytes:
            return False
        self.m_idxWrite += numOfBytes
        return True

    # 현재 데이터 사이즈
    @property
    def NowDataSize(self):
        return self.m_idxWrite - self.m_idxRead

    # 현재 남은 사이즈
    @property
    def NowRemainSize(self):
        return len(self.m_buffer) - self.m_idxWrite

    # 현재 읽을 세그먼트
    @property
    def NowReadSegment(self):
        return memoryview(self.m_buffer)[self.m_idxRead:self.m_idxRead + self.NowDataSize]

    # 현재 쓸 세그먼트
    @property
    def NowWriteSegment(self):
        return memoryview(self.m_buffer)[self.m_idxWrite:self.m_idxWrite + self.NowRemainSize]