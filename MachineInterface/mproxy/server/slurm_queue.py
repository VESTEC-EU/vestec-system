from .job_status import JobStatus

class SlurmQueueProcessor:
    def getQueueStatusSummaryCommand(self):
        return "squeue"

    def getQueueStatusForSpecificJobsCommand(self, queue_ids):
        job_queue_str=""
        for queue_id in queue_ids:
            job_queue_str+=queue_id+","
        return "sacct --format jobid,elapsed,state -j "+job_queue_str

    def getSubmissionCommand(self, scriptname):
        return "sbatch "+scriptname

    def getJobDeletionCommand(self, jobID):
        return "scancel "+jobID

    def isStringQueueId(self, raw_str):
        return raw_str.isnumeric() and "." not in raw_str

    def parseQueueStatus(self, queue_raw_data):
        jobs={}
        header_data=queue_raw_data.split('\n')[0]
        print(header_data.split())
        print(len(header_data.split()))
        if len(header_data.split()) == 3:
            print('parse sacct')
            # sacct data
            for line in queue_raw_data.split('\n'):                
                tokens=line.split()
                print(tokens)
                if len(tokens) >=3 and self.isStringQueueId(tokens[0]):                        
                    print('sacct', self.isStringQueueId(tokens[0]), self.getConvertSlurmAccountingJobStatusCode(tokens[2]))
                    jobs[tokens[0]]=JobStatus(tokens[0], self.getConvertSlurmAccountingJobStatusCode(tokens[2]), tokens[1] if tokens[1] != "0:00" else "") 
        else:
            print('parse squeue')
            # squeue data
            for line in queue_raw_data.split('\n'):                
                tokens=line.split()
                print(tokens)
                if len(tokens) >=6 and self.isStringQueueId(tokens[0]):
                    jobs[tokens[0]]=JobStatus(tokens[0], self.getConvertSlurmQueueJobStatusCode(tokens[4]), tokens[5] if tokens[5] != "0:00" else "")                    

        print('parseQueueStatus', jobs)
        return jobs

    def getSummaryOfMachineStatus(self, job_queue_info):
        status={}
        for value in list(job_queue_info.values()):            
            if value.getStatus() not in status:
                status[value.getStatus()]=0
            status[value.getStatus()]+=1
        return status

    def getConvertSlurmQueueJobStatusCode(self, job_queue_str):        
        if (job_queue_str == "PD"): return "QUEUED"
        if (job_queue_str == "R"): return "RUNNING"
        if (job_queue_str == "RD"): return "HELD"
        if (job_queue_str == "CD"): return "COMPLETED"
        if (job_queue_str == "CG"): return "ENDING"
        return "UNKNOWN"

    def getConvertSlurmAccountingJobStatusCode(self, job_queue_str):        
        if (job_queue_str == "PENDING"): return "QUEUED"
        if (job_queue_str == "RUNNING"): return "RUNNING"
        if (job_queue_str == "SUSPENDED"): return "HELD"
        if (job_queue_str == "COMPLETED"): return "COMPLETED"        
        return "UNKNOWN"
