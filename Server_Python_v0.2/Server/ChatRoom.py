from typing import List, Callable

class JobQueue:
    def __init__(self):
        self.queue = []

    def push(self, job: Callable):
        self.queue.append(job)

    def execute(self):
        while self.queue:
            job = self.queue.pop(0)
            job()


class ChatRoom:
    # 생성자
    def __init__(self):
        self.m_liSessions: List["ClientSession"] = []
        self.m_queue = JobQueue()
        self.m_liWaitPackets: List["IPacket"] = []

    # 작업 큐에 작업 추가
    def push(self, job: Callable):
        self.m_queue.push(job)

    # Flush
    def flush(self):
        for session in self.m_liSessions:
            PacketMgrServer.instance().send(session, self.m_liWaitPackets)

        if len(self.m_liWaitPackets) > 0:
            print(f"Flushed {len(self.m_liWaitPackets)} items")

        self.m_liWaitPackets.clear()

    # 방송 (Broadcast)
    def broadcast(self, session: "ClientSession", msg: str):
        pass
        # p = S2CAckChat()
        # p.uid = session.sessionID
        # p.message = "I am " + str(p.uid)
        # self.m_liWaitPackets.append(p)

    # 입장 (Enter)
    def enter(self, session: "ClientSession"):
        self.m_liSessions.append(session)
        session.setChatRoom(self)

    # 퇴장 (Leave)
    def leave(self, session: "ClientSession"):
        if session in self.m_liSessions:
            self.m_liSessions.remove(session)
