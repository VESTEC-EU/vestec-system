from .job_status import JobStatus
import time
import datetime
from dateutil.parser import parse

class SlurmQueueProcessor:
    def getQueueStatusSummaryCommand(self):
        return "squeue"

    def getQueueCommandForHistoricalStatus(self, start, end):
        return "sacct -a -S "+start+" -E "+end+" --format=JobID,ReqNodes,State,Submit,Start,TimeLimit"

    def getQueueStatusForSpecificJobsCommand(self, queue_ids):
        job_queue_str=""
        for queue_id in queue_ids:
            job_queue_str+=queue_id+","
        return "squeue --states=all --job "+job_queue_str

    def getSubmissionCommand(self, scriptname):
        return "sbatch "+scriptname

    def getJobDeletionCommand(self, jobID):
        return "scancel "+jobID

    def isStringQueueId(self, raw_str):
        return raw_str.isnumeric() and "." not in raw_str

    def doesSubmissionReportContainQueueId(self, raw_str):
        salt="Submitted batch job"
        if salt in raw_str:
            id_code=raw_str[raw_str.index(salt) + len(salt):]
            return id_code.strip().isnumeric()
        return False

    def extractQueueIdFromSubmissionReport(self, raw_str):
        salt="Submitted batch job"
        if salt in raw_str:
            id_code=raw_str[raw_str.index(salt) + len(salt):]
            return id_code.strip()
        return ""

    def parseQueueStatus(self, queue_raw_data):
        jobs={}
        header_data=queue_raw_data.split('\n')[0]
        if len(header_data.split()) == 7:
            # sacct data
            for line in queue_raw_data.split('\n'):                
                tokens=line.split()
                if len(tokens) >=7 and self.isStringQueueId(tokens[0]):                        
                        jobs[tokens[0]]=JobStatus(tokens[0], self.getConvertSlurmAccountingJobStatusCode(tokens[2]), tokens[1] if tokens[1] != "0:00" else "N/A", tokens[3], tokens[4], tokens[5], tokens[6])
        else:
            # squeue data
            for line in queue_raw_data.split('\n'):                
                tokens=line.split()
                if len(tokens) >=6 and self.isStringQueueId(tokens[0]):
                    jobs[tokens[0]]=JobStatus(tokens[0], self.getConvertSlurmQueueJobStatusCode(tokens[4]), tokens[5] if tokens[5] != "0:00" else "N/A", tokens[6], "Unknown", "Unknown", "Unknown")                    

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

    def parseHistorialStatus(self, queue_raw_data):
        jobs=""        
        for line in queue_raw_data.split('\n'):
            tokens=line.split()
            if len(tokens) >= 5 and self.isStringQueueId(tokens[0]):                
                if tokens[3] != "Unknown" and tokens[4] != "Unknown" and tokens[5] != "":                    
                    submit=time.mktime(parse(tokens[3]).timetuple())
                    start=time.mktime(parse(tokens[4]).timetuple())
                    extra_hours=0
                    if ("-" in tokens[5]):
                        sp=tokens[5].split("-")
                        try:
                            pt=parse(sp[1])
                        except (ParseError):
                            pt=None
                        extra_hours=24 * int(sp[0])
                    else:
                        try:
                            pt=parse(tokens[5])
                        except (ParseError):
                            pt=None
                    if (pt is not None):
                        jobs+=tokens[0]+" "+tokens[1]+" "+str(start-submit)+" " +str(pt.second + pt.minute*60 + (pt.hour+extra_hours)*3600)+"\n"
        return jobs
