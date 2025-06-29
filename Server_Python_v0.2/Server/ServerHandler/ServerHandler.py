from ServerHandler.ScheduleManager import  ScheduleManager


class serverHandler:

    @staticmethod
    def ProcC2SReqReadAttendancePlans(session, packet):
        query = (f"SELECT * FROM attendance WHERE uuid={packet.uid} "
                 f"AND start_date<=CURRENT_DATE ORDER BY version DESC LIMIT 1")
        
        def callback(dt):
            li = []
            remainChangeNum = 0
            if dt:
                row = dt[0]
                remainChangeNum = int(row['num_remain_chage'])
                
                weekdays = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
                for i, day in enumerate(weekdays, 1):
                    if row[f'{day}_active']:
                        startTime = row[f'{day}_start_time'].strftime("%H:%M:%S")
                        endTime = row[f'{day}_end_time'].strftime("%H:%M:%S")
                        li.append(AttendancePlan(i, startTime, endTime))
            
            response_packet = S2CAckReadAttendancePlans(remainChangeNum, li)
            PacketMgrServer.Instance().Send(session, response_packet)
        
        DBMgr.Inst().Request(query, callback)

        @staticmethod
        def ProcC2SReqReadAttendanceLogs(session, packet):
            uid = packet.uid
            start = packet.startDate
            end = packet.endDate
            query = f"""
            SELECT 
            ci.uuid AS uuid,
            COALESCE(ci.attendance_date, co.attendance_date) AS attendance_date,
            ci.check_in_time AS check_in_time,
            ci.planned_time AS planned_check_in_time,
            ci.status AS check_in_status,
            ci.reason AS check_in_reason,
            co.check_out_time AS check_out_time,
            co.planned_time AS planned_check_out_time,
            co.status AS check_out_status,
            co.reason AS check_out_reason
        FROM attendance_date_check_in_history AS ci
        LEFT JOIN attendance_date_check_out_history AS co
        ON ci.uuid = co.uuid AND ci.attendance_date = co.attendance_date
        WHERE ci.uuid = {uid} AND COALESCE(ci.attendance_date, co.attendance_date) BETWEEN '{start}' AND '{end}'
        UNION
        SELECT 
            co.uuid AS uuid,
            COALESCE(ci.attendance_date, co.attendance_date) AS attendance_date,
            ci.check_in_time AS check_in_time,
            ci.planned_time AS planned_check_in_time,
            ci.status AS check_in_status,
            ci.reason AS check_in_reason,
            co.check_out_time AS check_out_time,
            co.planned_time AS planned_check_out_time,
            co.status AS check_out_status,
            co.reason AS check_out_reason
        FROM attendance_date_check_out_history AS co
        LEFT JOIN attendance_date_check_in_history AS ci
        ON co.uuid = ci.uuid AND co.attendance_date = ci.attendance_date
        WHERE co.uuid = {uid} AND COALESCE(ci.attendance_date, co.attendance_date) BETWEEN '{start}' AND '{end}';
        """
        def callback(dt):
            logs = []
            for row in dt:
                inDate = row['attendance_date'].strftime("%Y-%m-%d")
                inTime = row['check_in_time'].strftime("%H:%M:%S") if row['check_in_time'] else ""
                inPlannedTime = row['planned_check_in_time'].strftime("%H:%M:%S") if row['planned_check_in_time'] else ""
                inStat = row['check_in_status'] if row['check_in_status'] else "없음"
                inReason = row['check_in_reason'] if row['check_in_reason'] else ""
                
                outTime = row['check_out_time'].strftime("%H:%M:%S") if row['check_out_time'] else ""
                outPlannedTime = row['planned_check_out_time'].strftime("%H:%M:%S") if row['planned_check_out_time'] else ""
                outStat = row['check_out_status'] if row['check_out_status'] else "없음"
                outReason = row['check_out_reason'] if row['check_out_reason'] else ""
                
                status_map = {"정상": 1, "자율": 2, "지각": 3, "결석": 4, "조퇴": 3}
                inResult = status_map.get(inStat, 0)
                outResult = status_map.get(outStat, 0)
                
                logs.append(AttendanceLog(inDate, inTime, inPlannedTime, inResult, inReason,
                                          outTime, outPlannedTime, outResult, outReason))
            
            response_packet = S2CAckReadAttendanceLogs(logs)
            PacketMgrServer.Instance().Send(session, response_packet)
        
        DBMgr.Inst().Request(query, callback)
