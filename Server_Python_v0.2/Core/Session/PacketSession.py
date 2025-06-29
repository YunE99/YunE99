import struct
from abc import abstractmethod
from Core.Session.BaseSession import BaseSession


class PacketSession(BaseSession):
    def OnRecv(self, buffRecv: bytearray, t: int = None) -> int:
        """
        패킷을 수신하여 처리하는 메서드 (오버로딩 구현).
        """
        if isinstance(buffRecv, bytes):
            # bytes 타입의 데이터를 처리하는 경우
            buffRecv = bytearray(buffRecv)  # bytes를 bytearray로 변환
            return self.OnRecv(buffRecv, t)  # 변환된 데이터를 다시 호출
        
        proccessLength = 0
        numPackets = 0  # For Test

        while True:
            if len(buffRecv) < 2:  # [패킷 크기] 2byte
                break
            
            packetSize = struct.unpack_from('<H', buffRecv, 0)[0]
            if packetSize > len(buffRecv):
                break
            if packetSize == 0:
                break

            self.OnRecv(buffRecv[:packetSize])  # 해당 패킷 처리
            numPackets += 1
            proccessLength += packetSize
            buffRecv = buffRecv[packetSize:]  # 패킷 크기만큼 버퍼 이동

        # (1 < numPackets) # For Test
        # print(f"패킷 모아보내기 : {numPackets}") # For Test
        return proccessLength

    # @@ 수신 @@
    def ProcPacket(self, buffRecv: bytearray):
        """
        패킷 타입을 확인하고 적절한 핸들러를 호출하는 메서드.
        """
        if buffRecv is None:
            return

        # 패킷 타입 추출
        packetType = struct.unpack_from('<H', buffRecv, 2)[0]

        # 패킷 타입에 따른 처리 (주석된 부분 변환)
        # if packetType == ePacketType.eC2SReqUserInfo:
        #     C2SReqUserInfo().Read(buffRecv)
        # elif packetType == ePacketType.eS2CAckUserInfo:
        #     S2CAckUserInfo().Read(buffRecv)

        self.OnRecv(buffRecv)  # 수신 처리

    @abstractmethod
    def OnRecv(self, buffRecv: bytearray):
        """
        하위 클래스에서 구현해야 하는 패킷 처리 메서드.
        """
        pass

    # Getter & Setter
    @property
    def SessionID(self):
        return self.m_sessionID

    def SetSessionID(self, id: int):
        self.m_sessionID = id
