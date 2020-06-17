class PBSQueueProcessor:
    def getQueueStatusSummaryCommand(self):
        return "qstat"

    def getQueueStatusForSpecificJobsCommand(self, queue_ids):
        job_queue_str=""
        for queue_id in queue_ids:
            job_queue_str+=queue_id+" "
        return "qstat -H "+job_queue_str

    def getSubmissionCommand(self, scriptname):
        return "qsub -q short "+scriptname

    def getJobDeletionCommand(self, jobID):
        return "qdel "+jobID

    def isStringQueueId(self, raw_str):
        return ".sdb" in raw_str

    def parseQueueStatus(self, queue_raw_data):
        jobs={}        

        for line in queue_raw_data.split('\n'):
            if ".sdb" in line:
                tokens=line.split()
                if (len(tokens) < 8):
                    jobs[tokens[0]]=self.getConvertPBSJobStatusCode(tokens[4])
                else:
                    jobs[tokens[0]]=self.getConvertPBSJobStatusCode(tokens[9])

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
        if (job_queue_str == "F"): return "COMPLETED"
        if (job_queue_str == "E"): return "ENDING"
        return "UNKNOWN"