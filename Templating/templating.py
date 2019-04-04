import jinja2
import os
dir_path = os.path.dirname(os.path.realpath(__file__))

class Templates():
    def __init__(self):
        loader = jinja2.FileSystemLoader(os.path.join(dir_path,"templates"))
        self.env = jinja2.Environment(loader=loader)

    def render_template(self,file,**kwargs):
        t = self.env.get_template(file)
        return t.render(**kwargs)





if __name__ == "__main__":

    t=Templates()

    pbs={"walltime":"00:20:00", "jobname":"test", "nodes":"16", "budget":"z19-cse"}
    modules="module swap PrgEnv-cray PrgEnv-gnu"
    omp="4"
    command = "aprun -n 96 -d 4 -S 3 ./exe"

    print t.render_template("pbs.j2",pbs=pbs,modules=modules,omp=omp,command=command)
