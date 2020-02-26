import workflow
import pony.orm as pny
from db import Incident
import datetime
import time
import sys
import uuid
import os

sys.path.append("../")

from ConnectionManager import RemoteConnection
import simulation

# we now want to define some handlers
@workflow.handler
def fire_terrain_handler(message):
    print("In Fire terrain handler")
    time.sleep(1)

    workflow.send(message=message, queue="fire_simulation")


@workflow.handler
def fire_hotspot_handler(message):
    print("In Fire hotspot handler")
    time.sleep(1)

    workflow.send(message=message, queue="fire_simulation")


@workflow.atomic
@workflow.handler
def fire_simulation_handler(message):
    incident = message["IncidentID"]

    print("In fire simulation handler")

    workflow.Persist.Put(incident=incident, data={"originator": message["originator"]})

    records = workflow.Persist.Get(incident)

    test = 0
    terrain = 1
    hotspot = 2
    weather = 4

    for record in records:
        if record["originator"] == "weather_results_handler":
            test = test | weather
            print("   Weather data available")
        elif record["originator"] == "fire_terrain_handler":
            test = test | terrain
            print("   Terrain data available")
        elif record["originator"] == "fire_hotspot_handler":
            test = test | hotspot
            print("   Hotspot data available")

    if test == terrain | hotspot | weather:
        #if the "remote" item in the message is True we want to submit to a HPC machine
        if message["remote"]:
            print("Will execute fire simulation remotely")
            workflow.send(message,"fire_submit_job")
        else:
            print("Running Fire Simulation")
            time.sleep(1)
            workflow.send(message=message, queue="fire_results")
    else:
        print("Will do nothing - waiting for data")

#submits a dummy job to a HPC machine
@workflow.handler
def fire_submit_job_handler(message):
    
    incident = message["IncidentID"]

    machine = "ARCHER"
    
    #create database entry for the simulation and set the properties
    simID = simulation.Create(incident)
    simulation.SetResultsHandler(simID,"remote_fire_results")
    simulation.SetMachine(simID,machine,"short",os.path.join(incident,simID))
    simulation.SetJobProperties(simID,nodes=1,walltime=datetime.timedelta(minutes=20))
    
    #open remote connection to the HPC machine
    c = RemoteConnection(machine)
    
    #create working directories for the simulation (incidentID/SimID)
    c.mkdir(incident)
    c.cd(incident)
    c.mkdir(simID)
    c.cd(simID)

    # Write a wee python script that we run on the HPC machine
    f=c.OpenRemoteFile("script.py","w")
    f.write("import time\n")
    f.write("\n")
    f.write("time.sleep(300)\n")
    f.write("f=open('output.dat','w')\n")
    f.write("f.write('lots of fire - simulated remotely!')\n")
    f.write("f.close()\n")
    f.close()
    
    #write the PBS script
    f=c.OpenRemoteFile("submit.pbs","w")
    f.write('''
#!/bin/bash --login

#PBS -N fire
#PBS -l select=1
#PBS -l walltime=00:20:00
#PBS -q short

#PBS -A d170

module load python-compute

export PBS_O_WORKDIR=$(readlink -f $PBS_O_WORKDIR)               

cd $PBS_O_WORKDIR


export OMP_NUM_THREADS=1


aprun -n 1 python script.py
    ''')
    f.close()
    
    #run the qsub command
    stdout,stderr,exit_status = c.ExecuteCommand("qsub submit.pbs")
    
    #if this went successfully, set the PBS jobID to the simulation database
    if stderr == "":
        pbsid=stdout.strip("\n")
        simulation.SetJobID(simID,pbsid)
        simulation.UpdateSimulationStatus(simID,"SUBMITTED")
        print("Submitted remote job %s"%pbsid)
    else:
        print("Some error occured. Error message:")
        print(stderr)

    return


workflow.RegisterHandler(fire_submit_job_handler,"fire_submit_job")


@workflow.handler
def fire_results_handler(msg):
    incident=msg["IncidentID"]

    print("Fire simulation results available")
    time.sleep(1)
    
    workflow.Complete(incident)

workflow.RegisterHandler(fire_results_handler,"fire_results")

#Get simulation results from HPC machine
@workflow.handler
def remote_fire_results_handler(msg):
    incident=msg["IncidentID"]

    print("Remote simulation results available!")

    machine = msg["machine"]
    wkdir = msg["wkdir"]
    
    #open connection to the machine
    c=RemoteConnection(machine)
    
    #cd to the simulations working directory
    c.cd(wkdir)
    
    #read the output file
    f=c.OpenRemoteFile("output.dat","r")
    data=f.readlines()
    f.close()

    print("Simulation results are:")
    print("--------------------------------------------------------------------------------")
    for line in data:
        print(line)
    print("--------------------------------------------------------------------------------")

    #complete the workflow
    workflow.Complete(incident)

workflow.RegisterHandler(remote_fire_results_handler,"remote_fire_results")




# we have to register them with the workflow system
workflow.RegisterHandler(fire_terrain_handler, "fire_terrain")
workflow.RegisterHandler(fire_hotspot_handler, "fire_hotspot")
workflow.RegisterHandler(fire_simulation_handler, "fire_simulation")
