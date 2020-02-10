import workflow
import uuid
import pony.orm as pny
import datetime
import time


def submit_fire(id):

    # create a basic message dictionary
    msg = {}
    msg["IncidentID"] = id
    msg["data"] = "blah blah blah"

    # send the messages to relevant queues to kick off the workflow
    workflow.send(message=msg, queue="fire_terrain")
    workflow.send(message=msg, queue="fire_hotspot")
    workflow.send(message=msg, queue="weather_data")

    workflow.FlushMessages()


if __name__ == "__main__":
    id = workflow.CreateIncident(name="test fire", kind="FIRE")
    submit_fire(id)
    workflow.finalise()
