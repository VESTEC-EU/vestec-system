from Database import machine
from Database import job
import pony.orm as pny
from Database import db, initialiseDatabase

@pny.db_session
def initialiseStaticInformation():
  pny.delete(m for m in machine.Machine)
  pny.delete(m for m in machine.NodeDescription)
  pny.delete(mf for mf in machine.NodeTechnology)
  pny.delete(m for m in machine.TechnologyArchitecture)
  pny.delete(m for m in job.SubmittedJob)
  pny.delete(m for m in job.Activity)

  archer_cpu_tech=machine.TechnologyArchitecture(microarchitecture="Ivy Bridge", manufacturer="Intel",
                                                 clockrate_mhz=2700, type=machine.MachineComponent.CPU, generation=6)
  archer_node_cpu=machine.NodeTechnology(technology=archer_cpu_tech, cores_per_node=24)
  archer_node_standard_mem=machine.NodeDescription(node_count=4544, memory_GB_per_node=64,
                                                   technologies=[archer_node_cpu])
  archer_node_high_mem = machine.NodeDescription(node_count=376, memory_GB_per_node=128,
                                                 technologies=[archer_node_cpu])

  cirrus_cpu_tech= machine.TechnologyArchitecture(microarchitecture="Broadwell", manufacturer="Intel",
                                                  clockrate_mhz=2100, type=machine.MachineComponent.CPU, generation=8)
  cirrus_node_cpu=machine.NodeTechnology(technology=cirrus_cpu_tech, cores_per_node=36)
  cirrus_node=machine.NodeDescription(node_count=280, memory_GB_per_node=256,
                                                   technologies=[cirrus_node_cpu])

  machine.Machine(name="ARCHER", node_description=[archer_node_standard_mem,
                                                   archer_node_high_mem])
  machine.Machine(name="Cirrus", node_description=[cirrus_node])

def generate():
    initialiseDatabase()
    #db.drop_all_tables(with_all_data=True)
    initialiseStaticInformation()

if __name__ == "__main__":
    generate()
