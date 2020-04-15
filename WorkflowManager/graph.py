import pony.orm as pny
import sys
sys.path.append("../")
from Database.workflow import MessageLog
from Database import initialiseDatabase
import sys
import os
import datetime

import networkx as nx
import pygraphviz as pgv
from networkx.drawing.nx_agraph import graphviz_layout, to_agraph

#extracts message logs from an incident and produces a plot of the workflow graph
def main(incident):
    #directional graph structure to store the graph
    G=nx.DiGraph()

    with pny.db_session:
        messages = pny.select(m for m in MessageLog if m.incident_id == incident)[:]

        for m in messages:
            originator = m.originator
            destination = m.destination

            #remove handler or queue suffixes from names if present (just for cosmetic reasons)
            originator= originator.replace("_handler","")
            destination = destination.replace("_queue","")

            #if the src and dest tags are present, use these as node names instead of the originator and destination fields
            if m.src_tag != "":
                originator = m.src_tag
            if m.dest_tag != "":
                destination = m.dest_tag

            #don't display any handlers internal to the workflow system
            if originator[0] == "_":
                continue

            #create nodes and join them together
            G.add_node(originator,style="filled",fillcolor="chartreuse") #originator clearly called successfully

            if m.status == "SENT":
                colour="white"
            elif m.status == "COMPLETE":
                colour = "chartreuse"
            elif m.status == "PROCESSING":
                colour = "orange"
            elif m.status == "ERROR":
                colour = "red"
            else:
                colour = "grey"
            G.add_node(destination,style="filled",fillcolor=colour)
            G.add_edge(originator,destination)

    for n in G:
        completion_time = sum((m.completion_time for m in messages if m.destination==n),
                              datetime.timedelta(0))
        G.nodes[n]['label'] = n + "\n" + str(completion_time)

    A = to_agraph(G)
    print(A)
    A.layout('dot')
    A.draw('%s.png'%incident)
    os.system("open %s.png"%incident)





if __name__ == "__main__":
    initialiseDatabase()

    if len(sys.argv) ==2:
        incident = sys.argv[1]
        main(incident)

    print("Please provide an incident UUID.")
