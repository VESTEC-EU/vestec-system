from Database import db
import pony.orm as pny
from enum import Enum

class MachineComponent(Enum):
  CPU=1
  GPU=2
  OTHER=3

class TechnologyArchitecture(db.Entity):
  facet=pny.Optional("NodeTechnology")
  microarchitecture=pny.Required(str)
  manufacturer=pny.Required(str)
  clockrate_mhz=pny.Required(int)
  type=pny.Required(MachineComponent)
  generation=pny.Required(int)

class NodeTechnology(db.Entity):
  node_description = pny.Optional("NodeDescription")
  technology = pny.Required(TechnologyArchitecture)
  cores_per_node = pny.Required(int)

class NodeDescription(db.Entity):
  machine = pny.Optional("Machine")
  node_count=pny.Required(int)
  memory_GB_per_node = pny.Required(int)
  technologies=pny.Set("NodeTechnology")

class Machine(db.Entity):
  jobs = pny.Set("SubmittedJob")
  name = pny.Required(str)
  node_description = pny.Set("NodeDescription")
