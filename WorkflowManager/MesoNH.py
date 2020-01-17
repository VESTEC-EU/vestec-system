import workflow
import time

#dummy variable to persist state of weather simulation
weather_done=False


#define some handlers for each stage in the workflow
@workflow.handler
def weather_data_handler(message):
    print("In weather data handler")
    time.sleep(1)
    workflow.send(queue='weather_simulation', message=message)
    

@workflow.handler
def weather_simulation_handler(message):
    print("In weather simulation handler")
    time.sleep(1)
    workflow.send(queue='weather_results', message=message)


@workflow.handler
def weather_results_handler(message):
    print("In weather results handler")
    time.sleep(1)
    
    global weather_done
    weather_done=True

    workflow.send(queue='fire_simulation', message=message)


#register these with the workflow system
workflow.RegisterHandler(weather_data_handler,"weather_data")
workflow.RegisterHandler(weather_simulation_handler,"weather_simulation")
workflow.RegisterHandler(weather_results_handler,"weather_results")

