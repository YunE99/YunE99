import threading
from Server.Session import DBSession

class DBSessionMgr:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """ 싱글톤 패턴 적용 """
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(DBSessionMgr, cls).__new__(cls)
                    cls._instance.__initialized = False
        return cls._instance

    def __init__(self):
        """ 중복 초기화 방지 """
        if not self.__initialized:
            self.m_lock = threading.Lock()
            self.m_session = None
            self.__initialized = True  # 한번만 초기화

    def Generate(self):
        """ 세션 생성 """
        with self.m_lock:
            self.m_session = DBSession()
            return self.m_session
        
    def Find(self):
        """ 세션 찾기 """
        with self.m_lock:
            return self.m_session
        
    def Remove(self, param):
        """ 
        세션 제거 (C#의 오버로딩 대응) 
        - 정수 ID 제거
        - 세션 객체 제거
        """
        with self.m_lock:
            if isinstance(param, int) or isinstance(param, DBSession):
                self.m_session = None

# 싱글톤 객체 사용 예시
db_mgr = DBSessionMgr()
