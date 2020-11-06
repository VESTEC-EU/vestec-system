import os

class logfile():
    def __init__(self,logdir):
        self.logdir = logdir
    def __enter__(self):
        self.f=open(os.path.join(self.logdir,"tests.log"),"a")
        return self.f
    def __exit__(self,type,value,traceback):
        self.f.close()

def logTest(name,result, logdir,message=None):
    with logfile(logdir) as f:
        if message is None:
            print("    %s: %s"%(result,name))
            f.write("    %s: %s\n"%(result,name))
        else:
            f.write("    %s: %s - %s\n"%(result,name, message))
            print("    %s: %s - %s"%(result,name, message))