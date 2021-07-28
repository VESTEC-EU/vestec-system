import json
import pony.orm as pny
import sys
sys.path.append("../")

from Database.workflow import HandlerLog

try:
    from . import utils
except Exception: #ImportError
    import utils

logger = utils.GetLogger(__name__)

#### Code for a database to be used to store state information for the handlers

# Class that allows handlers to log some data that persists after that handler has exited
class _Persist:
    def __init__(self):
        pass

    # Called by handler... logs information to be persisted between calls
    def Put(self, incident, data):
        originator = sys._getframe(1).f_code.co_name

        try:
            data = json.dumps(data)
        except TypeError:
            logger.error("workflow.Persist.Put: Cannot jsonify data")
            raise Exception("workflow.Persist.Put: Cannot jsonify data") from None

        with pny.db_session:
            HandlerLog(incident=incident, originator=originator, data=data)
        logger.debug(
            "Handler %s persisted some data for incident %s" % (originator, incident)
        )

    # called by handler - retrieives all the logs belonging to this incident and handler
    def Get(self, incident, ignoreOriginator=False):
        originator = sys._getframe(1).f_code.co_name
        logger.debug(
            "Handler %s requesting data from incident %s" % (originator, incident)
        )
        with pny.db_session:
            if (ignoreOriginator):
                logs = HandlerLog.select(
                    lambda p: p.incident == incident
                )
            else:
                logs = HandlerLog.select(
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
            pny.delete(l for l in HandlerLog if l.incident == incident)
        logger.info("Cleaned up persistance data for incident %s" % incident)
