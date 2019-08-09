from Database.machine import Machine
from Database.queues import Queue
import pony.orm as pny
from Database import db, initialiseDatabase
from uuid import uuid4

@pny.db_session
def initialiseStaticInformation():
    pny.delete(m for m in Machine)
    pny.delete(q for q in Queue)

    archer_id = str(uuid4())
    archer = Machine(machine_id=archer_id, machine_name="ARCHER", host_name="login.archer.ac.uk", 
                     scheduler="PBS", num_nodes=4920, cores_per_node=24, base_work_dir="/work/d170/d170")

    cirrus_id = str(uuid4())
    cirrus = Machine(machine_id=cirrus_id, machine_name="CIRRUS", host_name="cirrus.epcc.ed.ac.uk", 
                     scheduler="PBS", num_nodes=280, cores_per_node=36, base_work_dir="/lustre/home/????")

    pny.commit()

    archer_queue1 = Queue(queue_id=str(uuid4()), queue_name="standard", machine_id=archer_id, max_nodes=4920,
                          min_walltime=60, max_walltime=86400, default=1)

    archer_queue2 = Queue(queue_id=str(uuid4()), queue_name="long", machine_id=archer_id, max_nodes=256,
                          min_walltime=86400, max_walltime=172800, default=0)

    archer_queue3 = Queue(queue_id=str(uuid4()), queue_name="short", machine_id=archer_id, max_nodes=8,
                          min_walltime=60, max_walltime=1200, default=0)

    archer_queue4 = Queue(queue_id=str(uuid4()), queue_name="low", machine_id=archer_id, max_nodes=512,
                          min_walltime=60, max_walltime=10800, default=0)

    archer_queue5 = Queue(queue_id=str(uuid4()), queue_name="largemem", machine_id=archer_id, max_nodes=376,
                          min_walltime=60, max_walltime=172800, default=0)

    archer_queue6 = Queue(queue_id=str(uuid4()), queue_name="serial", machine_id=archer_id, max_nodes=1,
                          min_walltime=60, max_walltime=86400, default=0)

    cirrus_queue1 = Queue(queue_id=str(uuid4()), queue_name="workq", machine_id=cirrus_id, max_nodes=70,
                          min_walltime=60, max_walltime=345600, default= 1)

    cirrus_queue2 = Queue(queue_id=str(uuid4()), queue_name="indy", machine_id=cirrus_id, max_nodes=15,
                          min_walltime=60, max_walltime=1209600, default=0)

    cirrus_queue3 = Queue(queue_id=str(uuid4()), queue_name="large", machine_id=cirrus_id, max_nodes=280,
                          min_walltime=60, max_walltime=172800, default=0)

    pny.commit()

def generate():
    initialiseDatabase()
    initialiseStaticInformation()

if __name__ == "__main__":
    generate()
