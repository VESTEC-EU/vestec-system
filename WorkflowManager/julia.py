import numpy as np
import matplotlib.pyplot as plt
from numba import jit
import datetime
import os

import workflow

#calculates a julia set (accellerated by numba)
@jit(nopython=True)
def julia(cx, cy, nx=200, nits=256):
    x = np.linspace(-2.0, 2.0, nx)
    y = x

    img = np.zeros((nx, nx))

    for i in range(len(x)):
        for j in range(len(y)):
            yy = y[j]
            xx = x[i]

            n = 0
            while xx * xx + yy * yy < 100.0 and n < nits:

                # z_{n+1} = z_{n}^2 + C = (x^2 -y^2 + cx) + (2*x*y + cy)i

                zx = xx * xx - yy * yy + cx
                zy = 2 * xx * yy + cy

                n += 1

                xx = zx
                yy = zy

            img[i, j] = n

    return img


#calculates a julia set for C = cx + iCy
@workflow.handler
def julia_calculate_handler(msg):
    incident = msg["IncidentID"]

    wkdir = incident

    cx = msg["cx"]
    cy = msg["cy"]
    nits = msg["nits"]
    nx = msg["nx"]
    coords = msg["coords"]

    print("Calculating Julia set for %f + %fi" % (cx, cy))
    data = julia(cx, cy, nits=nits, nx=nx)

    fname = os.path.join(wkdir, "julia_" + coords + ".png")

    plt.imsave(fname, data, vmin=0, vmax=nits / 8)

    msg["filename"] = fname

    workflow.send(msg, "julia_stitch_queue")

    return




#sees if all the sets are completed. If so, stitches them into a big image
@workflow.atomic
@workflow.handler
def julia_stitch_handler(msg):
    incident = msg["IncidentID"]
    wkdir = incident

    n = msg["nimgs"]

    coords = msg["coords"]
    filename = msg["filename"]
    nnx = msg["nimgsx"]
    nny = msg["nimgsy"]
    nx = msg["nx"]

    data = {"coords": coords, "filename": filename}

    # workflow.Persist.Put(incident, data)

    # records = workflow.Persist.Get(incident)

    # print("%d of %d" % (len(records), n))

    files=os.listdir(wkdir)
    c=0
    for f in files:
        if "julia_" in f:
            c+=1


    if c == n:
        print("We can stitch the picture together now :)")
        workflow.Complete(incident)
        #print(files.sort())
        files.sort()
        f=open("images.txt","w")
        for file in files:
            f.write(os.path.join(wkdir,file)+" ")
        f.close()

        cmd = "montage @images.txt -tile %dx%d -geometry %dx%d+0+0 out.png" % (
            nnx,
            nny,
            nx,
            nx,
        )
        print(cmd)
        os.system(cmd)
        os.system("open out.png")
        os.system("rm -r %s"%wkdir)
        os.system("rm images.txt")
        
    else:
        print("Not all files are ready")
        # nothing to do yet
        return





#Entry point to the workflow. Determines the images that need to be made, then sends messages to make them
@workflow.handler
def julia_request_handler(msg):
    incident = msg["IncidentID"]

    workflow.Persist.Put(incident, data={"Called": True})
    records = workflow.Persist.Get(incident)
    if len(records) > 1:
        raise Exception("Julia set alreay requested for this incident")

    wkdir = incident
    # make working directory
    os.mkdir(wkdir)

    # centre of final mosaic
    centre = msg["centre"]
    # range of final mosaic (e.g. img extends to centre-range : centre+range)
    ranges = msg["range"]

    # number of images
    nimgs = msg["nimgs"]

    nnx = msg["nimgsx"]
    nny = msg["nimgsy"]

    # resolution of individual images (pixels)
    nx = msg["nx"]
    nits = msg["nits"]

    x = np.linspace(centre[0] - ranges, centre[0] + ranges, nnx)
    y = np.linspace(centre[1] - ranges, centre[1] + ranges, nny)
    print("x = ", x)
    print("y = ", y)

    for i in range(len(x)):
        for j in range(len(y)):
            coords = "%05d_%05d" % (i, j)
            cx = x[i]
            cy = y[j]

            msg["coords"] = coords
            msg["cx"] = cx
            msg["cy"] = cy

            print("Requesting julia set be made for %s: %f + %fi" % (coords, cx, cy))

            workflow.send(msg, "julia_calculate_queue")

    # workflow.Complete(incident)





def Start(nnx=5, nx=50, nits=256, centre=[0, 0], range=2):
    incident = workflow.CreateIncident(name="julia", kind="JULIA")

    msg = {}

    msg["IncidentID"] = incident
    msg["centre"] = centre
    msg["range"] = range
    msg["nimgsx"] = nnx
    msg["nimgsy"] = nnx
    msg["nimgs"] = nnx * nnx
    msg["nx"] = nx
    msg["nits"] = nits

    workflow.send(msg, "julia_request_queue")
    workflow.FlushMessages()

    return


def RegisterHandlers():
    workflow.RegisterHandler(julia_calculate_handler, "julia_calculate_queue")
    workflow.RegisterHandler(julia_request_handler, "julia_request_queue")
    workflow.RegisterHandler(julia_stitch_handler, "julia_stitch_queue")


if __name__ == "__main__":
    workflow.OpenConnection()
    RegisterHandlers()
    Start(nnx=25, centre=[-0.5, 0], range=1.5)
    workflow.CloseConnection()
    
