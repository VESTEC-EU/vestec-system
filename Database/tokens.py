from Database import db
import pony.orm as pny
import datetime
from Database import User

class Token(db.Entity):
    jti=pny.Required(str)
    date_created = pny.Required(datetime.datetime)
    date_accessed = pny.Required(datetime.datetime)
    user = pny.Required(User)
