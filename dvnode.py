import sys
import time
import threading

#global variables
neighbors = {}
routing_table = {}
last_node = False
local_port = 0

def node_receiver():
     pass


def check_port_num(port_num):
        #check for invalid port #
        try:
            int(port_num)
        except:
             sys.exit("> [ERROR: Port number not an integer]")
        if not 1024<=int(port_num)<=65535:
            sys.exit("> [ERROR: Port number out of range, needs to be in range 1024-65535]")
        
        return int(port_num)

def check_rate_loss(rate_loss):
     #check for invalid rate_loss
        try:
            float(rate_loss)
        except:
             sys.exit("> [ERROR: Rate loss not a float]")

        if not 0.0<=float(rate_loss)<=1.0:
            sys.exit("> [ERROR: Rate loss needs to be between 0.0-1.0]")
        
        return float(rate_loss)

def populate_neighbors():
    global neighbors, last_node
    #make sure that each neighbor pair is a valid port # and loss rate
    #add to the neighbor list as a tuple pair [port #, loss rate]
    last_node_factor = 1 if last_node else 0
    x = 2
    while(x<len(sys.argv)-last_node_factor):
         n_port = check_port_num(sys.argv[x])
         n_loss_rate = check_rate_loss(sys.argv[x+1])
         if n_port not in neighbors:
              neighbors[n_port] = n_loss_rate
         else:
              #throw error, can't use the same port twice
              sys.exit("> [ERROR: Can't have duplicate port neighbors]")
         x+=2

def get_timestamp():
    timestamp = time.time()
    formatted_timestamp = f"{timestamp:.3f}"
    return formatted_timestamp

def print_routing_table():
     timestamp = get_timestamp()
     print(f"[{timestamp}] Node <port-{local_port}> Routing Table")
     for node in routing_table:
          if node!=routing_table[node][1]:
               print(f"- ({routing_table[node][0]}) Node {node}; Next hop -> Node {routing_table[node][1]}")
          else:
               print(f"- ({routing_table[node][0]}) Node {node}")
            

# python dvnode.py <local-port> <neighbor1-port> <loss-rate-1> <neighbor2-port> <loss-rate-2> ... [last]
def main():
    global last_node, neighbors, routing_table, local_port
    
    #check we have the minimum amount of args >= 4(program name, local port, n1-port, lr-1)
    if len(sys.argv)<4:
        sys.exit("> [ERROR: Not enough arguments, must specify at least one neighbor]")
    
    #check the local-port #
    local_port = check_port_num(sys.argv[1])

    #check to see if last argument is last
    if(sys.argv[len(sys.argv)-1]=="last"):
        last_node = True
    
    #check each pair of neighbors
    #for n in n-pairs: check that 
    if(last_node):
         if(len(sys.argv)%2!=1):
               sys.exit("> [ERROR: Incorrect number of arguments]")
         
    else:
         if(len(sys.argv)%2!=0):
               sys.exit("> [ERROR: Incorrect number of arguments]")
    
    #populate our neighbor list
    populate_neighbors()

    #build the initial routing table and display
    for neighbor in neighbors:
         routing_table[neighbor] = [neighbors[neighbor], neighbor]

    #print the initial routing table
    print_routing_table()

    #start receiver thread

#run main
if __name__ == "__main__":
    main()


