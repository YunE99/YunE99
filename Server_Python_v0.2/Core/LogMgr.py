import os
from datetime import datetime

class LogMgr:
    # Singleton Instance
    g_instance = None

    def __init__(self):
        if LogMgr.g_instance is not None:
            raise Exception("This class is a singleton!")
    
    @staticmethod
    def Instance():
        if LogMgr.g_instance is None:
            LogMgr.g_instance = LogMgr()
        return LogMgr.g_instance

    def Write(self, _msg):
        nowDate = datetime.now()

        # 시간
        todayDate = nowDate.strftime("%y%m%d")
        fullDate = nowDate.strftime("%y년 %m월 %d일 %H시 %M분 %S초")
        tag = f"[{fullDate}]"

        # 파일 이름
        fileName = f"{todayDate}Log.txt"

        try:
            # 파일이 존재하는지 확인 후 파일 열기 (추가 모드)
            with open(fileName, "a", encoding="utf-8") as streamWriter:
                streamWriter.write(tag + _msg + "\n")
        except Exception as e:
            pass  # 예외 발생 시 무시 (C# 코드와 동일한 처리)
