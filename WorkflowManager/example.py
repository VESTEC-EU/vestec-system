import workflow

#send the messages to relevant queues to kick off the workflow
workflow.send(message="Dummy Message",queue="fire_terrain")
workflow.send(message="Dummy Message",queue="fire_hotspot")
workflow.send(message="Dummy Message",queue="weather_data")

workflow.finalise()
