import threading
import queue
from typing import Callable
from abc import ABC, abstractmethod
import time

class IJobQueue(ABC):
    @abstractmethod
    def Push(self, job: Callable) -> None:
        pass
    
class JobQueue(IJobQueue):
    def __init__(self):
        self.m_queue = queue.Queue()  # 객체로 초기화
        self.m_lock = threading.Lock()
        self.m_isFlush = False

    # PUSH
    def Push(self, job: Callable) -> None:
        isFlush = False
        with self.m_lock:  # Lock을 acquire하고, 이후 release는 자동으로 처리
            self.m_queue.put(job)
            if not self.m_isFlush:
                isFlush = self.m_isFlush = True

        if isFlush:
            self.Flush()

    # Flush
    def Flush(self) -> None:
        while True:
            ac = self.Pop()
            if ac is None:
                return
            ac()

    # POP
    def Pop(self) -> Callable:
        with self.m_lock:  # Lock을 acquire하고, 이후 release는 자동으로 처리
            if self.m_queue.empty():
                self.m_isFlush = False
                return None
            return self.m_queue.get()

# 사용 예시    
if __name__ == "__main__":

    def sample_job():
        print("Job executed")

    job_queue = JobQueue()
    job_queue.Push(sample_job)  # 대소문자 맞춰서 호출
    time.sleep(1)  # 실행 완료 확인을 위해 잠시 대기

    print("JobQueue test completed")  # 테스트 완료 출력
