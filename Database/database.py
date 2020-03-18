import pony.orm as pny
from pony.orm.dbapiprovider import StrConverter
from enum import Enum
import os
import time

db = pny.Database()


class EnumConverter(StrConverter):
    def validate(self, val, a):
        if not isinstance(val, Enum):
            raise ValueError("Must be an Enum.  Got {}".format(type(val)))
        return val

    def py2sql(self, val):
        return val.name

    def sql2py(self, value):
        # Any enum type can be used, so py_type ensures the correct one is used to create the enum instance
        return self.py_type[value]


def initialiseDatabase():
    if "VESTEC_DB_TYPE" in os.environ:
        dbtype = os.environ["VESTEC_DB_TYPE"]
        print("Setting up database type '%s'" % dbtype)
        if dbtype == "sqlite":
            if "VESTEC_DB_PATH" not in os.environ:
                raise Exception("The enviroment variable VESTEC_DB_PATH is not set")
            dbpath = os.environ["VESTEC_DB_PATH"]
            try:
                db.bind("sqlite", dbpath, create_db=True)
            except pny.core.BindingError:
                print("Warning: attempting to bind to the database more than once")
                return

        elif dbtype == "mysql":
            if "VESTEC_DB_SERVER" not in os.environ:
                raise Exception("The enviroment variable VESTEC_DB_SERVER is not set")
            if "VESTEC_DB_PORT" not in os.environ:
                raise Exception("The enviroment variable VESTEC_DB_PORT is not set")
            if "VESTEC_DB_USER" not in os.environ:
                raise Exception("The enviroment variable VESTEC_DB_USER is not set")
            if "VESTEC_DB_PASSWD" not in os.environ:
                raise Exception("The enviroment variable VESTEC_DB_PASSWD is not set")
            if "VESTEC_DB_NAME" not in os.environ:
                raise Exception("The enviroment variable VESTEC_DB_NAME is not set")

            dbserver = os.environ["VESTEC_DB_SERVER"]
            dbport = int(os.environ["VESTEC_DB_PORT"])
            dbuser = os.environ["VESTEC_DB_USER"]
            dbpasswd = os.environ["VESTEC_DB_PASSWD"]
            dbname = os.environ["VESTEC_DB_NAME"]
            print("Database parameters:")
            print(" - server   = %s" % dbserver)
            print(" - port     = %s" % dbport)
            print(" - user     = %s" % dbuser)
            # print(" - password = %s"%dbpasswd)
            print(" - database = %s" % dbname)

            tries = 0
            while tries < 5:
                try:
                    db.bind(
                        provider="mysql",
                        host=dbserver,
                        port=dbport,
                        user=dbuser,
                        password=dbpasswd,
                        db=dbname,
                    )
                    break
                except pny.core.BindingError:
                    print("Warning: attempting to bind to the database more than once")
                    return
                except:
                    print("Failed to connect to db... trying again in 5 seconds")
                    time.sleep(5)
                    tries += 1
            if tries == 5:
                raise Exception("Unable to connect to database :(")
            print("Database connection established :)")

        else:
            raise Exception("Unknown database type '%s'" % dbtype)

    else:
        print(
            "WARNING: No environment variable set. Defaulting to use a local sqlite database"
        )
        dbpath = "vestec.sqlite"
        try:
            db.bind("sqlite", dbpath, create_db=True)
        except pny.core.BindingError:
            print("Warning: attempting to bind to the database more than once")
            return

    db.provider.converter_classes.append((Enum, EnumConverter))
    # Generate object mapping
    db.generate_mapping(create_tables=True)
    print("Database initialised")
