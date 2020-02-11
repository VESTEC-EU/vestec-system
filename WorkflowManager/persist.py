import json
import pony.orm as pny
import sys

#### Code for a database to be used to store state information for the handlers

# Class that allows handlers to log some data that persists after that handler has exited
class _Persist:
    localDB = pny.Database()

    class DBlog(localDB.Entity):
        incident = pny.Required(str)
        originator = pny.Required(str)
        data = pny.Required(str)

    def __init__(self):
        self.localDB.bind(provider="sqlite", filename="handlers.sqlite", create_db=True)
        # self.localDB.bind(provider='sqlite', filename=":memory:") #cannot have an in-memory db if used between many processes
        self.localDB.generate_mapping(create_tables=True)

    # Called by handler... logs information to be persisted between calls
    def Put(self, incident, dict):
        originator = sys._getframe(1).f_code.co_name
        try:
            data = json.dumps(dict)
        except:
            raise Exception("workflow.Persist.Put: Cannot jsonify data")
        with pny.db_session:
            self.DBlog(incident=incident, originator=originator, data=data)

    # called by handler - retrieives all the logs belonging to this incident and handler
    def Get(self, incident):
        originator = sys._getframe(1).f_code.co_name
        with pny.db_session:
            logs = self.DBlog.select(
                lambda p: p.incident == incident and p.originator == originator
            )
            l = []
            for log in logs:
                dict = json.loads(log.data)
                l.append(dict)
        return l

    # Cleans up any logs associated with an incident
    def _Cleanup(self, incident):
        with pny.db_session:
            pny.delete(l for l in self.DBlog if l.incident == incident)
        print(" [*] Cleaned up persistance for incident %s" % incident)
