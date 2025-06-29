import threading
from collections import defaultdict
from Core.Session.PacketSession import PacketSession

class UserMgr:
    _g_instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.m_dicUID = {}
        self.m_dicSession = {}
        self._dic_lock = threading.Lock()

    @classmethod
    def Instance(cls):
        if cls._g_instance is None:
            with cls._lock:
                if cls._g_instance is None:
                    cls._g_instance = cls()
        return cls._g_instance

    def Login(self, session: PacketSession, deviceType: int, uid: int) -> bool:
        isResult = True
        sessionID = session.SessionID

        with self._dic_lock:
            if sessionID in self.m_dicSession:
                print(f"중복 로그인 : {sessionID}")
                isResult = False
            elif uid in self.m_dicUID:
                user = self.m_dicUID[uid]
                if deviceType == 1:  # 태블릿
                    user.SetTablet(session)
                    self.m_dicSession[sessionID] = user
                    if user.sessionTablet is not None:
                        print(f"중복 2차 로그인(태블릿) 통과 [uid:{user.uid}] [태블릿(NEW):{user.sessionTablet.SessionID}]")
                    else:
                        print(f"2차 로그인(태블릿) [uid:{user.uid}] [태블릿(NEW):{user.sessionTablet.SessionID}] [모바일(OLD):{user.sessionMobile.SessionID}]")
                else:  # 모바일
                    user.SetMobile(session)
                    self.m_dicSession[sessionID] = user
                    if user.sessionMobile is not None:
                        print(f"중복 2차 로그인(모바일) 통과 [uid:{user.uid}] [모바일(NEW):{user.sessionMobile.SessionID}]")
                    else:
                        print(f"2차 로그인(모바일) [uid:{user.uid}] [태블릿(OLD):{user.sessionTablet.SessionID}] [모바일(NEW):{user.sessionMobile.SessionID}]")
            else:
                user = UserData(session, deviceType, uid)
                self.m_dicUID[uid] = user
                self.m_dicSession[sessionID] = user
                print(f"신규 로그인 [uid:{uid}] [sessionID:{session.SessionID}]")

        return isResult

    def Logout(self, session: PacketSession):
        sessionID = session.SessionID
        user = None

        with self._dic_lock:
            user = self.m_dicSession.pop(sessionID, None)

            if user:
                if user.sessionTablet and sessionID == user.sessionTablet.SessionID:
                    print(f"태블릿 로그아웃 : [uid:{user.uid}] [sessionID:{user.sessionTablet.SessionID}]")
                    user.SetTablet(None)

                if user.sessionMobile and sessionID == user.sessionMobile.SessionID:
                    print(f"모바일 로그아웃 : [uid:{user.uid}] [sessionID:{user.sessionMobile.SessionID}]")
                    user.SetMobile(None)

                if user.sessionTablet is None and user.sessionMobile is None:
                    print(f"최종 로그아웃 : [uid:{user.uid}]")
                    self.m_dicUID.pop(user.uid, None)

    def GetUser(self, key):
        with self._dic_lock:
            if isinstance(key, PacketSession):
                return self.m_dicSession.get(key.SessionID)
            elif isinstance(key, int):
                return self.m_dicUID.get(key)
            return None

    def GetSessions(self, key):
        result = []
        with self._dic_lock:
            if isinstance(key, PacketSession):
                user = self.m_dicSession.get(key.SessionID)
            elif isinstance(key, int):
                user = self.m_dicUID.get(key)
            else:
                user = None

            if user:
                if user.sessionTablet:
                    result.append(user.sessionTablet)
                if user.sessionMobile:
                    result.append(user.sessionMobile)

        return result
