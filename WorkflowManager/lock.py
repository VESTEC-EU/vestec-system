import pony.orm as pny
import datetime
import functools
import json

#####A semaphore lock for if a handler needs to ensure it is the only version of it running at once

# database for the locks
lockDB = pny.Database()


class Lock(lockDB.Entity):
    name = pny.PrimaryKey(str)
    date = pny.Optional(datetime.datetime)
    locked = pny.Required(bool, default=False)


lockDB.bind(provider="sqlite", filename="locks.sqlite", create_db=True)
lockDB.generate_mapping(create_tables=True)

# check that an entry for this handler exists in the lock database
def _EnsureLockHandlerExists(name):
    with pny.db_session:
        if Lock.exists(name=name):
            return
        else:
            print(" [*] Creating LockDB entry for %s" % name)
            Lock(name=name)
            return


# This function gets a lock and returns once it has it
# Takes a name/label for the lock, and the incident this belongs to. Combines these to create a
# unique ID for the name
def GetLock(name, incident):
    if name == None or incident == None:
        raise Exception("Unable to lock: Lock requires a name and incident")
    else:
        name = name + incident

    # make sure there is an entry for this handler in the db
    _EnsureLockHandlerExists(name)

    # loop until we get a lock
    while True:
        with pny.db_session:
            l = Lock[name]
            if l.locked == False:
                l.locked = True
                l.date = datetime.datetime.now()
                print(" [*] Aquired Lock")
                return
            else:
                print(" [*] Lock not aquired. Will try again in 1 second")
        time.sleep(1)


# Checks if we can get a lock. If so, we get one and returns true, otherwise returns false
def CheckLock(name, incident):
    if name == None or incident == None:
        raise Exception("Unable to lock: Lock requires a name and incident")
    else:
        name = name + incident

    # make sure there is an entry for this handler in the db
    _EnsureLockHandlerExists(name)

    with pny.db_session:
        l = Lock[name]
        if l.locked == False:
            l.locked = True
            l.date = datetime.datetime.now()
            print(" [*] Aquired Lock")
            return True
        else:
            return False


# this function releases a lock
# Takes a name/label for the lock, and the incident this belongs to. Combines these to create a
# unique ID for the name
def ReleaseLock(name, incident):
    if name == None or incident == None:
        raise Exception("Lock requires a name and an incident")
    else:
        name = name + incident

    try:
        with pny.db_session:
            l = Lock[name]
            l.locked = False
            l.date = datetime.datetime.now()
            print(" [*] Lock released")
    except:
        raise Exception("Unable to unlock: unknown lock")


# a wrapper version of the above two functions for handlers so you can wrap a function/handler
# If we cannot get a lock we reject the message (re-queueing it)
def atomic(f):
    @functools.wraps(f)
    def wrapper(ch, method, properties, body, **kwargs):
        msg = json.loads(body)
        # If we get the lock, run the handler
        if CheckLock(f.__name__, msg["IncidentID"]):
            try:
                f(ch, method, properties, body, **kwargs)
            finally:
                #we want to make sure that if the handler (or its @workflow.handler boilerplate) dies that the lock is still released
                ReleaseLock(f.__name__, msg["IncidentID"])
        else:
            # reject the message
            print(" [*] Lock for %s not acquired. Requeueing" % f.__name__)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    return wrapper


def _CleanLock(incident):
    with pny.db_session:
        pny.delete(l for l in Lock if incident in l.name)
    print(" [*] Cleaned up locks for incident %s" % incident)
