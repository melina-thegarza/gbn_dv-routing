import sys
import time
import threading
import socket
import json
import os

#global variables
neighbors = {}
routing_table = {}
last_node = False
local_port = 0
receiver_ip = "0.0.0.0"

def node_receiver(node_socket):
     #listen for incoming messages
     while(True):
          #handle message
          message = node_socket.recvfrom(65535)
          message = message[0].decode()

          #sending node port 
          sender_port = message.split(" ",1)[0]

          #sender's routing table
          sender_routing_table = json.loads(message.split(" ",1)[1])

          #routing message received
          print(f"[{get_timestamp()}] Message received at Node <port-{local_port}> from Node <port-{sender_port}>")

          #handle the received routing table
          receive_routing_table(sender_port,sender_routing_table)

def receive_routing_table(sender_port,sender_routing_table):
     global routing_table

     for destination, values in sender_routing_table.items():
          #make sure we are not adding the node itself to its own routing table
          if int(destination)!=local_port:
            #new potential cost
            total_cost = values[0] + routing_table[int(sender_port)][0]
            if destination not in routing_table or total_cost < routing_table[destination][0]:
                routing_table[destination] = [total_cost,values[1]]
     #print the updated routing_table
     print_routing_table()

     #if there is a change in the routing table or it is the first round
     # a node should send the updated info to its neighbors
     #update_neighbors()



# def update_neighbors():
#      pass

          
     
def node_sender(node_socket, kickoff):
     #kickoff the process
     if kickoff:
          #send routing table to neighbors
          for node in neighbors:
               #data packet should include
               #(1) sending node port, (2) most recent routing table
               packet = f"{local_port} {json.dumps(routing_table)}"

               #send packet
               timestamp = get_timestamp()
               print(f"[{timestamp}] Message sent from Node <port-{local_port}> to Node <port-{node}>")
               node_socket.sendto(str.encode(packet),(receiver_ip,node))

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

    ####
    #create the node socket
    #bind to 0.0.0.0
    node_ip = '0.0.0.0'

    #create a socket
    node_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        
    #bind to ip address & port
    node_socket.bind((node_ip,local_port))

    #start receiver thread
    receiver_thread = threading.Thread(target=node_receiver, args=(node_socket,))
    receiver_thread.start()

    #if you are the last node, kick off the algorithm
    if last_node:
        sender_thread = threading.Thread(target=node_sender, args=(node_socket,True))
        sender_thread.start()

    #wait for CTRL C to exit
    try:
        while True:
             pass

    except KeyboardInterrupt:
        print("\n...Exiting")
        os._exit(0)


#run main
if __name__ == "__main__":
    main()


