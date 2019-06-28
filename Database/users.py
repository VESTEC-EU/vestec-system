from Database import db
import pony.orm as pny

class User(db.Entity):
    username=pny.Required(str)
    name=pny.Required(str)
    passwordHash=pny.Required(str)
    email=pny.Required(str)
    accessRights=pny.Required(int)

    activities = pny.Set("Activity")

