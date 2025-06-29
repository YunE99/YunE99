from threading import Lock
from Server.Session.ClientSession import ClientSession

class ClientSessionMgr:
    _instance = None  # 싱글톤 인스턴스 저장

    @staticmethod
    def instance():
        """C#의 Instance 속성과 동일한 기능 제공"""
        if ClientSessionMgr._instance is None:
            ClientSessionMgr._instance = ClientSessionMgr()
        return ClientSessionMgr._instance

    def __init__(self):
        """싱글톤이므로 직접 호출을 방지"""
        if ClientSessionMgr._instance is not None:
            raise Exception("ClientSessionMgr는 싱글톤 클래스이므로 instance()를 사용하세요.")
        self.m_curSessionID = 0
        self.m_lock = Lock()
        self.m_dicSessions = {}

    # @@ 세션 생성 @@
    def generate(self):
        with self.m_lock:
            self.m_curSessionID += 1
            sessionID = self.m_curSessionID

            session = ClientSession()
            session.setSessionID(sessionID)
            self.m_dicSessions[sessionID] = session

            return session

    # @@ 세션 찾기 @@
    def find(self, id):
        with self.m_lock:
            return self.m_dicSessions.get(id, None)

    # @@ 세션 제거 @@
    def remove(self, id):
        with self.m_lock:
            if id in self.m_dicSessions:
                del self.m_dicSessions[id]

    def removeSession(self, session):
        with self.m_lock:
            if session.SessionID in self.m_dicSessions:
                del self.m_dicSessions[session.SessionID]


# # ✅ 사용 예시 (C# 스타일 유지)
# clientSessionMgr = ClientSessionMgr.instance()  # 싱글톤 객체 반환

# # 세션 생성 테스트
# session1 = clientSessionMgr.generate()


# # 생성된 세션 확인
# print("[ClientSessionMgr] Session 1 ID:", session1.SessionID)  # 1


# # 세션 찾기 테스트
# print("[ClientSessionMgr] Find Session 1:", clientSessionMgr.find(session1.SessionID) is not None)  # True

# # 세션 제거 테스트
# clientSessionMgr.remove(session1.SessionID)
# print("[ClientSessionMgr] Session 1 after removal:", clientSessionMgr.find(session1.SessionID) is None)  # True
