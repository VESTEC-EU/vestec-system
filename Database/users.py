from Database import db
import pony.orm as pny


class User(db.Entity):
    user_id = pny.Required(str)
    username = pny.Required(str)
    name = pny.Required(str)
    password_hash = pny.Required(str)
    email = pny.Required(str)
    access_rights = pny.Required(int, default=0)
    enabled = pny.Required(bool, default=False, sql_default='0')

    activities = pny.Set("Activity", cascade_delete=True)
    incidents = pny.Set("Incident")
    allowed_workflows=pny.Set("RegisteredWorkflow")

    pny.PrimaryKey(user_id, username)

