import workflow
import uuid
import pony.orm as pny
import datetime
import time
import sys

import fire


def submit_fire(id,remote=False):

    # create a basic message dictionary
    msg = {}
    msg["IncidentID"] = id
    msg["data"] = "blah blah blah"
    if remote:
        msg["remote"] = True
    else:
        msg["remote"] = False

    # send the messages to relevant queues to kick off the workflow
    workflow.send(message=msg, queue="fire_terrain")
    workflow.send(message=msg, queue="fire_hotspot")
    workflow.send(message=msg, queue="weather_data")

    workflow.FlushMessages()


if __name__ == "__main__":

    workflow.OpenConnection()
    fire.RegisterHandlers()

    id = workflow.CreateIncident(name="test fire", kind="FIRE")

    #If we used the remote argumnt when running this script, requests the workflow run a remote job
    if len(sys.argv) == 2:
        if sys.argv[1] == "remote":
            remote=True
        else:
            print("Unknown command line option")
            remote=False
    else:
        remote=False
    submit_fire(id,remote=remote)
    workflow.CloseConnection()
