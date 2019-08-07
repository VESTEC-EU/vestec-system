from Database.machine import Machine
import pony.orm as pny
from Database import db, initialiseDatabase
from uuid import uuid4

@pny.db_session
def initialiseStaticInformation():
    pny.delete(m for m in Machine)

    archer = Machine(machine_id=str(uuid4()), machine_name="ARCHER", host_name="login.archer.ac.uk", 
                     scheduler="PBS", num_nodes=4920, cores_per_node=24, base_work_dir="/work/d170/d170")
    cirrus = Machine(machine_id=str(uuid4()), machine_name="CIRRUS", host_name="cirrus.epcc.ed.ac.uk", 
                     scheduler="PBS", num_nodes=280, cores_per_node=36, base_work_dir="/lustre/home/????")

    pny.commit()

    # add queues

def generate():
    initialiseDatabase()
    initialiseStaticInformation()

if __name__ == "__main__":
    generate()
