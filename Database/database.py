import pony.orm as pny
from pony.orm.dbapiprovider import StrConverter
from enum import Enum

db = pny.Database()

class EnumConverter(StrConverter):
  def validate(self, val, a):
    if not isinstance(val, Enum):
      raise ValueError('Must be an Enum.  Got {}'.format(type(val)))
    return val

  def py2sql(self, val):
    return val.name

  def sql2py(self, value):
    # Any enum type can be used, so py_type ensures the correct one is used to create the enum instance
    return self.py_type[value]

def initialiseDatabase():
  db.bind("sqlite","vestec.sqlite",create_db=True)
  # Register the type converter with the database
  db.provider.converter_classes.append((Enum, EnumConverter))
  # Generate object mapping
  db.generate_mapping(create_tables=True)
  print("Database initialised")
