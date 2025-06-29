class SchedulerStatData:
    def __init__(self, scheduler, studyAmount, studySeconds):
        self.m_scheduler = scheduler
        self.m_studyAmount  = studyAmount
        self.m_studySeconds = studySeconds

    def Add(self, amount, seconds):
        self.m_studyAmount  += amount
        self.m_studySeconds += seconds

    @property
    def scheduler(self):
        return self.m_scheduler

    @property
    def StudyAmount(self):
        return self.m_studyAmount
    
    @property
    def StudySeconds(self):
        return self.m_studySeconds