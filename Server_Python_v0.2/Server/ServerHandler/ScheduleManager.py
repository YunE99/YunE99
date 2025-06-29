import datetime
from queue import Queue
from datetime import datetime, timedelta

class ScheduleManager:
    def __init__(self, session, packet, quSchedulers: Queue):
        self.m_session = session
        self.m_packet = packet
        self.m_quSchedulers = quSchedulers

        self.m_liSchedulers = []
        self.m_liSchedules = []

        self.m_dtToday = datetime.today().date()
        self.existTodaySchedule = False

        self.LoadSchedules()

    def Send(self):
        newPacket = S2CAckReadSchedulers(1, self.m_packet.startDate, self.m_packet.endDate, self.m_liSchedulers, self.m_liSchedules)
        PacketMgrServer.Instance.Send(self.m_session, newPacket)

    def LoadSchedules(self):
        if self.m_quSchedulers.empty():
            self.Send()
            return

        nowData = self.m_quSchedulers.get()
        nowScheduler = nowData.Scheduler
        self.m_liSchedulers.append(nowScheduler)

        self.existTodaySchedule = False
        today = self.m_dtToday

        startDate = datetime.strptime(nowScheduler.startDate, "%Y-%m-%d").date()
        endDate = datetime.strptime(nowScheduler.endDate, "%Y-%m-%d").date()

        if startDate <= today <= endDate:
            planSeconds = [
                nowScheduler.monSeconds, nowScheduler.tueSeconds, nowScheduler.wedSeconds,
                nowScheduler.thuSeconds, nowScheduler.friSeconds, nowScheduler.satSeconds, nowScheduler.sunSeconds
            ][today.weekday()]

            if planSeconds > 0:
                self.existTodaySchedule = True  # planSeconds가 0보다 클 때만 True로 설정

            DBMgr.Inst.Request(DBJob(
                f"SELECT * FROM schedules WHERE scheduler_id={nowData.Scheduler.pid}",
                lambda dt: self.processScheduleData(dt, nowData, planSeconds)
            ))
        else:
            self.LoadSchedules()

    def processScheduleData(self, dt, nowData, planSeconds):
        for _, row in dt.iterrows():
            pid = int(row["id"])
            sid = int(row["scheduler_id"])
            targetAmount = int(row["target_amount"])
            targetSeconds = int(row["target_seconds"])
            studyAmount = int(row["study_amount"])
            studySeconds = int(row["study_seconds"])
            pauseSeconds = int(row["pause_seconds"])
            restSeconds = int(row["rest_seconds"])
            outSeconds = int(row["out_seconds"])
            sleepSeconds = int(row["sleep_seconds"])
            isDone = int(row["is_done"])

            dtDate = datetime.strptime(row["date"], "%Y-%m-%d").date()
            strDate = dtDate.strftime("%Y-%m-%d")

            if planSeconds > 0 and self.m_dtToday == dtDate:
                self.existTodaySchedule = True  

            self.m_liSchedules.append(Schedule(
                pid, sid, strDate, targetAmount, targetSeconds, 
                studyAmount, studySeconds, pauseSeconds, restSeconds, 
                outSeconds, sleepSeconds, isDone
            ))
            nowData.add(studyAmount, studySeconds)

        if planSeconds > 0 and not self.existTodaySchedule:
            self.NewTodaySchedule(nowData, planSeconds)
        else:
            self.LoadSchedules()

    def NewTodaySchedule(self, data, plannedSeconds):
        scheduler = data.Scheduler
        targetAmount = 0

        if scheduler.startDate == scheduler.endDate:
            targetAmount = scheduler.startAmount
        elif scheduler.startAmount == scheduler.endAmount:
            targetAmount = scheduler.startAmount if scheduler.endAmount != 0 else 0
        else:
            if scheduler.endAmount == 0:
                remainAmount = scheduler.startAmount - data.StudyAmount
                if remainAmount > 0:
                    remainSeconds = self.GetRemainSecFromTodayToEndDate(scheduler)
                    remainMinute = remainSeconds / 60

                    amountPerSec = float(remainAmount) / remainSeconds
                    targetAmount = amountPerSec * plannedSeconds

        if targetAmount > 0:
            self.ReqInsertSchedule(scheduler, targetAmount, plannedSeconds)
        else:
            self.LoadSchedules()

    def GetRemainSecFromTodayToEndDate(self, data):
        remainSec = 0
        currentDate = self.m_dtToday
        finDate = datetime.strptime(data.endDate, "%Y-%m-%d").date()

        while currentDate <= finDate:
            remainSec += [
                data.monSeconds, data.tueSeconds, data.wedSeconds,
                data.thuSeconds, data.friSeconds, data.satSeconds, data.sunSeconds
            ][currentDate.weekday()]
            currentDate += timedelta(days=1)

        return remainSec

    def ReqInsertSchedule(self, scheduler, targetAmount, targetSeconds):
        query = (
            f"START TRANSACTION;\n"
            f"INSERT INTO schedules (uuid, scheduler_id, target_amount, target_seconds)\n"
            f"VALUES ({self.m_packet.uid}, {scheduler.pid}, {targetAmount}, {targetSeconds});\n"
            f"SELECT * FROM schedules WHERE id=LAST_INSERT_ID();\n"
            f"COMMIT;"
        )

        def callback(dt):
            if len(dt) > 0:
                row = dt.iloc[0]
                pid = int(row["id"])
                sid = int(row["scheduler_id"])
                date = pd.to_datetime(row["date"]).date().strftime("%Y-%m-%d")
                targetAmount = int(row["target_amount"])
                targetSeconds = int(row["target_seconds"])
                studyAmount = int(row["study_amount"])
                studySeconds = int(row["study_seconds"])
                pauseSeconds = int(row["pause_seconds"])
                restSeconds = int(row["rest_seconds"])
                outSeconds = int(row["out_seconds"])
                sleepSeconds = int(row["sleep_seconds"])
                isDone = int(row["is_done"])

                self.m_liSchedules.append(
                    Schedule(pid, sid, date, targetAmount, targetSeconds, studyAmount, studySeconds, pauseSeconds, restSeconds, outSeconds, sleepSeconds, isDone)
                )

            self.LoadSchedules()

        DBMgr.Inst.Request(DBJob(query, callback))
