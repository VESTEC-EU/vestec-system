import numpy as np
import matplotlib.pyplot as plt
import workflow
import json
import sys
import os

#create a list of n random numbers
def create_list(n=1000):
    x = np.random.random(n).tolist()
    print(x)
    return(x)

#quicksort (implemented normally - e.g. no workflows)
def quicksort(x,depth=0,maxdepth=1000):
    print("maxdepth=",maxdepth)
    if check(x):
        return x
    print("depth= %d"%depth)
    #print(x)

    if depth >=maxdepth:
        raise Exception("In too deep")

    #pick the last value as a pivot
    ref = x.pop()
    
    #create arrays for lower and upper
    x0=[]
    x1=[ref]
    for val in x:
        if val < ref:
            x0.append(val)
        else:
            x1.append(val)
    

    #sort each list
    x0=quicksort(x0,depth=depth+1,maxdepth=maxdepth)
    x1=quicksort(x1,depth=depth+1,maxdepth=maxdepth)

    #merge the two sorted lists together

    x= x0 + x1

    return x


def check(x):
    for i in range(len(x)-1):
        if x[i] > x[i+1]:
            return False
    return True

#logs a node and its children to json for analysis
#now replaced by the src_tag and dest_tag functionality of workflow.send
def logNodes(me,children):
    f=open("nodes.txt","a")
    d={}
    d["node"]=me
    d["children"]=children
    s=json.dumps(d)
    f.write(s+"\n")
    f.close()
    
def submit(n=100):
    incident=workflow.CreateIncident("quicksort","QUICKSORT")

    x = np.random.random(n).tolist()
   
    msg={}
    msg["IncidentID"]=incident
    msg["n"]=n
    msg["depth"]=0
    msg["position"]=0
    msg["x"]=x

    workflow.send(msg,"quicksort_queue",src_tag="Start",dest_tag="split_000_00000")
    
    #open nodes.txt in write mode to clear it
    f=open("nodes.txt","w")
    f.close()

    me="Start"
    children = ["split_000_00000"]
    #log the nodes (parent and child) of the workflow graph
    logNodes(me,children)

    workflow.FlushMessages()
    return



@workflow.handler
def quicksort_handler(msg):
    
    depth = msg["depth"]
    position = msg["position"]
    x=msg["x"]
    
    #plot initial unsorted array
    if (depth == 0):
        plt.close()
        plt.plot(x,".")
        plt.savefig("sorted.png")

    if check(x):
        me = "split_%03d_%05d"%(depth,position)
        child = "merge_%03d_%05d"%(depth,position//2)
        #log the parent node (this) and the child (one message is sent to) for graph visualisaiton
        logNodes(me,[child])
        workflow.send(msg,"merge_queue",src_tag=me,dest_tag=child)
        return

    
    #get last value in x
    pivot=x.pop()
    
    #create work arrays (put pivot at the start of x1)
    x0=[]
    x1=[pivot]
    
    #Sort x into x1 and x2
    for val in x:
        if val < pivot:
            x0.append(val)
        else:
            x1.append(val)

    
    #send messages

    me = "split_%03d_%05d"%(depth,position)
    child1 = "split_%03d_%05d"%(depth+1,2*position)
    child2 = "split_%03d_%05d"%(depth+1,2*position+1)

    msg["x"]=x0
    msg["depth"]=depth+1
    msg["position"]=2*position

    workflow.send(msg,"quicksort_queue",src_tag=me,dest_tag=child1)

    msg["x"]=x1
    msg["depth"]=depth+1
    msg["position"]=2*position+1

    workflow.send(msg,"quicksort_queue",src_tag=me,dest_tag=child2)

    logNodes(me,[child1,child2])

    return





@workflow.handler
def merge_handler(msg):
    #want to merge the positions 2n and 2n+1 into one list, then send this sortesd list to the merge handler at depth-1
    incident = msg["IncidentID"]
    depth = msg["depth"]
    position = msg["position"]
    originator=msg["originator"]
    x=msg["x"]

    print("depth = %d, position = %d"%(depth,position))

    #If we're at the top of the tree our array is sorted, and we can finish 
    if depth==0:
        print("Sorted :)")
        print(len(x))
        print(check(x))

        me = "merge_%03d_%05d"%(depth,position)
        logNodes(me,["End"])
        logNodes("End",[])

        plt.plot(x,'.')
        plt.savefig("sorted.png")
        plt.close()
        os.system("open sorted.png")
        workflow.Complete(incident)

        os.system("python nodes.py")
        
        return
    
    #Log the relevant data from the message we received
    record = {"depth" : depth, "position" : position, "x" : x}
    workflow.Persist.Put(incident,record)
    
    #get all the persisted data from this handler
    records=workflow.Persist.Get(incident)
    
    #we now want to check and see if we have the other array we need to merge
    mydepth=[]

    #search for records from the same depth
    for record in records:
        if record["depth"]==depth:
            mydepth.append(record)
    
    #determine the complimentary position we are looking for (we need position 2n and 2n+1 where n is an integer)
    if position%2 == 0: #we have 2n, we need 2n+1
        targetpos = position+1
        x0=x
        x1=[]
    else: #we have 2n+1, we need 2n
        targetpos = position-1
        x1=x
        x0=[]
    
    #search for the other array in the records
    test=False
    for record in mydepth:
        if record["position"] == targetpos:
            test=True
            #put the message array into the correct array for merging
            if targetpos%2 == 0:
                x0 = record["x"]
            else:
                x1 = record["x"]
    if test == False:
        #nothing to do yet, exit
        return
    else:
        #merge the arrays
        x = x0+x1
        if not check(x):
            print(x)
            raise Exception("x out of order")

        msg["depth"] = depth-1
        msg["position"]= position//2
        msg["x"] = x
        
        me = "merge_%03d_%05d"%(depth,position//2)
        child = "merge_%03d_%05d"%(depth-1,position//2//2)

        workflow.send(msg,"merge_queue",src_tag=me,dest_tag=child)

        
        logNodes(me,[child])

        return



def RegisterHandlers():
    workflow.RegisterHandler(quicksort_handler,"quicksort_queue")
    workflow.RegisterHandler(merge_handler,"merge_queue")



    





if __name__ == "__main__":
    workflow.OpenConnection()
    RegisterHandlers()
   
    submit(n=128)

    workflow.CloseConnection()


