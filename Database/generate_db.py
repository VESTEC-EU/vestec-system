from Database.machine import Machine
from Database.queues import Queue
import pony.orm as pny
from uuid import uuid4

@pny.db_session
def initialiseStaticInformation():
    pny.delete(m for m in Machine)
    pny.delete(q for q in Queue)

    archer = Machine(machine_id=str(uuid4()), machine_name="ARCHER", host_name="login.archer.ac.uk", 
                     scheduler="PBS", num_nodes=4920, cores_per_node=24, base_work_dir="/work/d170/d170")

    cirrus = Machine(machine_id=str(uuid4()), machine_name="CIRRUS", host_name="cirrus.epcc.ed.ac.uk", 
                     scheduler="PBS", num_nodes=280, cores_per_node=36, base_work_dir="/lustre/home/????")

    hpda = Machine(machine_id=str(uuid4()), machine_name="HPDA", host_name="fe-store01.sc.bs.dlr.de",
                   scheduler="SLURM", num_nodes=4, cores_per_node=56, base_work_dir="/home/holk_jo/VESTEC/VESTEC-install")

    pny.commit()

    archer.queues.create(queue_id=str(uuid4()), queue_name="standard", max_nodes=4920, min_walltime=60,
                         max_walltime=86400, default=1)

    archer.queues.create(queue_id=str(uuid4()), queue_name="long", max_nodes=256, min_walltime=86400,
                         max_walltime=172800, default=0)

    archer.queues.create(queue_id=str(uuid4()), queue_name="short", max_nodes=8, min_walltime=60,
                         max_walltime=1200, default=0)

    archer.queues.create(queue_id=str(uuid4()), queue_name="low", max_nodes=512, min_walltime=60,
                         max_walltime=10800, default=0)

    archer.queues.create(queue_id=str(uuid4()), queue_name="largemem", max_nodes=376, min_walltime=60,
                         max_walltime=172800, default=0)

    archer.queues.create(queue_id=str(uuid4()), queue_name="serial", max_nodes=1, min_walltime=60,
                         max_walltime=86400, default=0)

    cirrus.queues.create(queue_id=str(uuid4()), queue_name="workq", max_nodes=70, min_walltime=60,
                         max_walltime=345600, default= 1)

    cirrus.queues.create(queue_id=str(uuid4()), queue_name="indy", max_nodes=15, min_walltime=60,
                         max_walltime=1209600, default=0)

    cirrus.queues.create(queue_id=str(uuid4()), queue_name="large", max_nodes=280, min_walltime=60,
                         max_walltime=172800, default=0)

    
    hpda.queues.create(queue_id=str(uuid4()), queue_name="cpu", max_nodes=4, min_walltime=60,
                         max_walltime=604800, default=0)
    
    pny.commit()

