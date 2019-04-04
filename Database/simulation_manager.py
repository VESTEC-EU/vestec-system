import machine as machine
import job as job
import pony.orm as pny
from database import initialiseDatabase, db
import uuid

@pny.db_session
def testPersistentData():
  archer=machine.Machine.get(name='ARCHER')
  for i in archer.node_description:
    print(str(i.node_count))
  myactivity = job.Activity(name=str(uuid.uuid4()))
  myactivity.addSubmittedJob(archer, "test.exe", "Q123456")

  act = pny.select(a for a in job.Activity)
  for a in act:
      print(a.getName())


initialiseDatabase()
testPersistentData()
