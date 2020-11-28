from manager import workflow
import datetime

workflow.OpenConnection()

now = datetime.datetime.now()

IncidentID=workflow.CreateIncident(name="Tests for %s"%now,kind="TEST")

msg = {"IncidentID": IncidentID}

workflow.send(queue="spaceweather_init",message=msg)

workflow.FlushMessages()

workflow.CloseConnection()
