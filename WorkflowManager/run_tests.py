from manager import workflow
import datetime

workflow.OpenConnection()

now = datetime.datetime.now()

IncidentID=workflow.CreateIncident(name="Tests for %s"%now,kind="TEST")

msg = {"IncidentID": IncidentID, "testlist": ["workflow", "EDI","DM","SM"]}

workflow.send(queue="init_tests",message=msg)

workflow.FlushMessages()

workflow.CloseConnection()