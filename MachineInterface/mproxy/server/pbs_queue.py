class PBSQueueProcessor:
    def getQueueStatusCommand(self):
        return "qstat"

    def parseQueueStatus(self, queue_raw_data):
        jobs={}        

        for line in queue_raw_data.split('\n'):
            if ".sdb" in line:
                tokens=line.split()
                jobs[tokens[0]]=self.getConvertPBSJobStatusCode(tokens[4])                

        return jobs

    def getSummaryOfMachineStatus(self, job_queue_info):
        status={}
        for value in list(job_queue_info.values()):            
            if value not in status:
                status[value]=0
            status[value]+=1
        return status

    def getConvertPBSJobStatusCode(self, job_queue_str):
        if (job_queue_str == "Q"): return "QUEUED"
        if (job_queue_str == "R"): return "RUNNING"
        if (job_queue_str == "H"): return "HELD"
        return "UNKNOWN"