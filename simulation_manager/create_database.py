import database
import os

os.system("rm database/vestec.sqlite")
database.generate_db.generate()
