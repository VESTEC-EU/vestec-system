from Database import db
import pony.orm as pny

class LocalDataStorage(db.Entity):
    uuid = pny.PrimaryKey(int, auto=True)
    contents = pny.Required(bytes)
    filename=pny.Required(str)
    filetype=pny.Required(str)