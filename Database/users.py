from Database import db
import pony.orm as pny

class User(db.Entity):
    user_id = pny.PrimaryKey(str)
    user_name = pny.Required(str)
    name = pny.Required(str)
    password_hash = pny.Required(str)
    email = pny.Required(str)
    access_rights = pny.Required(int)

    activities = pny.Set("Activity")

