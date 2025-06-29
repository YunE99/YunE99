import struct
from collections import defaultdict
from typing import Dict, List, Type, Callable
from Core.Session.PacketSession import PacketSession

class PacketMgrServer:
    # Member Attributes
    m_dicAcRecvs: Dict[int, Callable[["PacketSession", bytes], None]] = {}
    m_dicAcProcs: Dict[int, Callable[["PacketSession", "IPacket"], None]] = {}

    # Singleton
    g_instance = None

    def __new__(cls):
        if cls.g_instance is None:
            cls.g_instance = super(PacketMgrServer, cls).__new__(cls)
            cls.g_instance.__init_instance()
        return cls.g_instance

    def __init_instance(self):
        self.Register()

    # Member Methods
    def Register(self):
        from PacketHandlerServer import PacketHandlerServer
        from ePacketType import ePacketType
        from packets import (
            C2SReqReadAttendancePlans, C2SReqReadAttendanceLogs, C2SReqAttendance,
            C2SReqGoHome, C2SReqBranchOn, C2SReqPoseResult, C2SReqPoseModify,
            C2SReqChatList, C2SReqReadDdayList, C2SReqWriteDday, C2SReqModifyDday,
            C2SReqDeleteDday, C2SReqReadStudyRests, C2SReqRestStart, C2SReqRestExtension,
            C2SReqRestEnd, C2SReqReadSchedulers, C2SReqWriteScheduler, C2SReqModifyScheduler,
            C2SReqDeleteScheduler, C2SReqSaveSchedule, C2SReqReadSubjects,
            C2SReqWriteSubject, C2SReqModifySubject, C2SReqDeleteSubject, C2SReqSortSubjects,
            C2SReqWriteAddHistory, C2SReqReadTextbooks, C2SReqWriteTextbook,
            C2SReqModifyTextbook, C2SReqDeleteTextbook, C2SReqUserLogin, C2SReqUserLogout,
            C2SReqReadSetting, C2SReqWritePeriodSec, C2SReqSignUp, C2SReqDuplChkId,
            C2SReqDuplChkPhone
        )
        
        packets_map = {
            ePacketType.eC2SReqReadAttendancePlans: (C2SReqReadAttendancePlans, PacketHandlerServer.ProcC2SReqReadAttendancePlans),
            ePacketType.eC2SReqReadAttendanceLogs: (C2SReqReadAttendanceLogs, PacketHandlerServer.ProcC2SReqReadAttendanceLogs),
            ePacketType.eC2SReqAttendance: (C2SReqAttendance, PacketHandlerServer.ProcC2SReqAttendance),
            ePacketType.eC2SReqGoHome: (C2SReqGoHome, PacketHandlerServer.ProcC2SReqGoHome),
            ePacketType.eC2SReqBranchOn: (C2SReqBranchOn, PacketHandlerServer.ProcC2SReqBranchOn),
            ePacketType.eC2SReqPoseResult: (C2SReqPoseResult, PacketHandlerServer.ProcC2SReqPoseResult),
            ePacketType.eC2SReqPoseModify: (C2SReqPoseModify, PacketHandlerServer.ProcC2SReqPoseModify),
            ePacketType.eC2SReqChatList: (C2SReqChatList, PacketHandlerServer.ProcC2SReqChatList),
            ePacketType.eC2SReqReadDdayList: (C2SReqReadDdayList, PacketHandlerServer.ProcC2SReqReadDdayList),
            ePacketType.eC2SReqWriteDday: (C2SReqWriteDday, PacketHandlerServer.ProcC2SReqWriteDday),
        }

        for packetType, (packetClass, handler) in packets_map.items():
            self.m_dicAcRecvs[packetType] = lambda session, buffRecv, cls=packetClass: self.MakePacket(session, buffRecv, cls)
            self.m_dicAcProcs[packetType] = handler

    def MakePacket(self, session: "PacketSession", buffRecv: bytes, packetClass: Type["IPacket"]):
        packet = packetClass()
        packet.Read(buffRecv)
        if packet.PacketType in self.m_dicAcProcs:
            self.m_dicAcProcs[packet.PacketType](session, packet)

    def OnRecvPacket(self, session: "PacketSession", buffRecv: bytes):
        if not buffRecv:
            return

        packetType = struct.unpack_from("H", buffRecv, 2)[0]
        if packetType in self.m_dicAcRecvs:
            self.m_dicAcRecvs[packetType](session, buffRecv)

    def Send(self, session: "PacketSession", packet: "IPacket"):
        sendBuff = packet.Write()
        session.Send(sendBuff)

    def SendMultiple(self, session: "PacketSession", packets: List["IPacket"]):
        segments = [packet.Write() for packet in packets]
        session.Send(segments)
