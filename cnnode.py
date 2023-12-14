import sys
import socket
import threading
import time
import json
import os
import random

#GLOBALS
receiver_ip = "0.0.0.0"
local_port = 0
last_node = False
base_case = False
routing_table = {}
#nodes we are receiving from
receiving_neighbors = {}
#nodes we are sending to
sending_neighbors = {}
#keep track of our various recv_bases for the different links
recv_bases = {}
#keep track of our various send_bases for the different links
send_bases = {}
#keep track, on the sender side the total amount of packets sent
num_packets_sent = {}
#keep track, on the sender the total amount of ACKS received
num_acks_received = {}
#timeout of 500 msec
TIMEOUT_INTERVAL = 0.5
#keep a timer for each probe receiver
timers = {}

import concurrent.futures
from concurrent.futures import ThreadPoolExecutor


# Define a lock
routing_table_lock = threading.Lock()

#The updates of routing table should only be sent out 1) for every 5 seconds (if there is any change in the
#rounded distances based on the newly calculated loss rate),
def every_5_seconds_update(node_socket):
     global num_packets_sent, num_acks_received, sending_neighbors
     while(True):
         # Acquire the lock before updating the routing table
        with routing_table_lock:
             #initially assume we will not send our neighbors an update
             should_send_update = False
             
             #get the loss rate
             for node in sending_neighbors:
                loss_count = num_packets_sent[node]-num_acks_received[node]
                try:
                    new_loss_rate = round(loss_count/num_packets_sent[node],2)
                except ZeroDivisionError:
                    new_loss_rate = 0.0
                #check if is different from the current distance in the routing table, if so update it
                current_loss_rate = routing_table[node][0]
                if current_loss_rate !=new_loss_rate:
                     routing_table[node] = [new_loss_rate,None]
                     should_send_update = True

        if should_send_update:
             update_neighbors(node_socket, False)
            
        #wait 5 seconds until next round of updates
        time.sleep(5)


def node_receiver(node_socket):
    # Use ThreadPoolExecutor for handling incoming packets
     with ThreadPoolExecutor(max_workers=10) as executor:
        #listen for incoming messages
        while(True):

            #handle message
            packet = node_socket.recvfrom(65535)
            #create thread to process message
            executor.submit(process_packet, node_socket, packet)
            # threading.Thread(target=process_packet, args=(node_socket,packet)).start()
         

def process_packet(node_socket,packet):
        probe_sender = packet[1][1]
        packet = packet[0].decode()

        #DIFFERENTIATE between receiving DV updates and receiving probe packets
        probe_packet = is_probe_packet(packet)
        #if we are receiving a probe packet, follow GBN
        #  drop probabilistically using the info in receiving_neighbors
        if probe_packet:
            #create thread to handle received probe_packet
            threading.Thread(target=handle_probe_packet, args=(node_socket,probe_sender,packet)).start()
        #DV Routing Table
        else:
            #sending node port 
            sender_port = packet.split(" ",1)[0]
            #sender's routing table
            sender_routing_table = json.loads(packet.split(" ",1)[1])
            #routing message received
            print(f"[{get_timestamp()}] Message received at Node <port-{local_port}> from Node <port-{sender_port}>")
            #handle the received routing table, create new thread
            threading.Thread(target=receive_routing_table, args=(sender_port,sender_routing_table,node_socket,)).start()

def handle_probe_packet(node_socket, probe_sender, packet):
          global recv_bases, timers
          packet = json.loads(packet)
          pkt_num = packet[0]
          data = packet[1]

          #check to see if this an ACK or msg
          ack_bit = (pkt_num >> 31) & 1
          pkt_num = (pkt_num & 0x7FFFFFFF)
          
          #if message, acknowledge, I'm probe_receiver
          if ack_bit==0:
            
            #if we drop pkts based on the probability of p
            #random.random generates a number between [0.0,1.0), only ACK if we don't drop packet
            value_of_p = receiving_neighbors[probe_sender]
            if not random.random() < value_of_p:
                    #check if pkt is received in correct order
                    if recv_bases[probe_sender]==pkt_num:
                         #send new ack
                         ack_thread = threading.Thread(target=node_ack_sender,args=(node_socket,probe_sender,pkt_num,False))
                         ack_thread.start()
                    else:
                         #retransmit old ack
                         ack_thread = threading.Thread(target=node_ack_sender,args=(node_socket,probe_sender,pkt_num,True))
                         ack_thread.start()

          #else ACK, process the ACK
          else:
            global send_bases, num_acks_received, timers
            #check if duplicate ack, don't move window
            if not pkt_num<send_bases[probe_sender]:
                #cumulative ack
                send_bases[probe_sender]=pkt_num+1
                #stop timer
                timers[probe_sender] = 0

            #add ack to num_acks_received count
            num_acks_received[probe_sender]+=1


def node_ack_sender(node_socket,probe_sender,pkt_num,out_of_order):
    global recv_bases

    #move window if not out_of_order
    if not out_of_order:
        recv_bases[probe_sender]+=1
        #form the packet, is an ACK
        seq = create_32_bit_seq_num(True,pkt_num)
        data = ''
        packet = [seq,data]
        #send ACK
        node_socket.sendto(str.encode(json.dumps(packet)),(receiver_ip,probe_sender))
    else:
        #make sure that recv_base is not at 0, if it is don't send ACK
        if recv_bases[probe_sender] != 0:
            #form packet
            seq = create_32_bit_seq_num(True,recv_bases[probe_sender]-1)
            data = ''
            packet = [seq,data]
            #send ACK
            node_socket.sendto(str.encode(json.dumps(packet)),(receiver_ip,probe_sender))


def receive_routing_table(sender_port,sender_routing_table, node_socket):
     global routing_table,base_case

     #store the original routing table, to see if it actually changes
     temp_routing_table = dict(routing_table)

     # Acquire the lock before updating the routing table
     with routing_table_lock:

        #if I'm receiving from the sender, update the direct link cost
        if int(sender_port) in receiving_neighbors:
             #make sure that there isn't a next hop, needs to be direct link update
             if sender_routing_table[str(local_port)][1] == None:

                #make sure that the direct link is better than the current hop link
                if(routing_table[int(sender_port)][1]!=None):
                        if(sender_routing_table[str(local_port)][0] < routing_table[int(sender_port)][0]):
                              routing_table[int(sender_port)] = [sender_routing_table[str(local_port)][0], None]
                #if direct link, and no hop, override to get updated loss rate
                elif routing_table[int(sender_port)][1]==None:
                     routing_table[int(sender_port)] = [sender_routing_table[str(local_port)][0], None]
              
             
        #iterate through DV update, update own routing table if we have a new shortest path
        for destination, values in sender_routing_table.items():
               #cast port destination to int
               destination = int(destination)

               #make sure we are not adding the node itself to its own routing table
               if destination!=local_port:

                     #round to second decimal place
                            #new potential cost, sender->destination + current_node->sender
                            total_cost = round((values[0] + routing_table[int(sender_port)][0]), 2)
                            #if destination not in routing_table 
                            if destination not in routing_table:
                                routing_table[destination] = [total_cost,int(sender_port)]
                            #if is already the next hop
                            elif int(sender_port)==routing_table[destination][1]:
                                 routing_table[destination] = [total_cost,int(sender_port)]
                            #not the original next hop, new distance must be smaller
                            else:
                                 #make sure that the link between current node and sender doesn't contain a hop
                                 if total_cost < routing_table[destination][0] and routing_table[int(sender_port)][1]==None:
                                       routing_table[destination] = [total_cost,int(sender_port)]
                                  
        
        #print the updated routing_table
        print_routing_table()

        #if there is a change in the routing table or it is the first round
        # a node should send the updated info to its neighbors
        if base_case==False or temp_routing_table!=routing_table:
               #check to see if this is the first DV update
               first_time = True if base_case==False else False
               #we have fulfilled the base_case
               base_case=True
               update_neighbors(node_socket, first_time)

def update_neighbors(node_socket,first_time):
     global local_port,routing_table, receiving_neighbors, sending_neighbors
     #send routing table to neighbors(neighbors in receiving_neighbors & sending_neighbors)
     for node in receiving_neighbors:
          #data packet should include
          #(1) sending node port, (2) most recent routing table
          packet = f"{local_port} {json.dumps(routing_table)}"

          #send packet
          timestamp = get_timestamp()
          print(f"[{timestamp}] Message sent from Node <port-{local_port}> to Node <port-{node}>")
          node_socket.sendto(str.encode(packet),(receiver_ip,node))   

     for node in sending_neighbors:
          #data packet should include
          #(1) sending node port, (2) most recent routing table
          packet = f"{local_port} {json.dumps(routing_table)}"

          #send packet
          timestamp = get_timestamp()
          print(f"[{timestamp}] Message sent from Node <port-{local_port}> to Node <port-{node}>")
          node_socket.sendto(str.encode(packet),(receiver_ip,node))


     #start sending probe packets if this is our first DV update
     if first_time:
          #create thread to print out status messages for loss rate every 1 second
          threading.Thread(target=packet_loss_rate_status_messages, args=()).start()

          #create a probe_sender thread, for each probe we are sending to
          for probe_receiver in sending_neighbors:
            probe_send_thread = threading.Thread(target=probe_sender,args=(node_socket,probe_receiver))
            probe_send_thread.start()
          
          #create thread to recalculate loss rates every 5 seconds and send updates if change is detected
          threading.Thread(target=every_5_seconds_update, args=(node_socket,)).start()   

def probe_sender(node_socket, probe_receiver):
    #  global send_base
    #going to need to create a separate thread for the timeout
     global send_bases, num_packets_sent, num_acks_received, timers
     
     #resend window is False until we timeout
     resend_window = False
     #set window size to 5
     window_size = 5
     #link sender_buffer
     sender_buffer = []
     #link sent_packet_numbers
     sent_packet_numbers = []
     
    #continuous loop through, we want to continously send probe packets
     #change to while(True)
     while (True):
        send_base = send_bases[probe_receiver]
        for pkt_num in range(send_base,window_size+send_base):
            #add probe packets to the sender_buffer, to handle culmulative ACK
            #we want a continous stream
            for _ in range(5):
                sender_buffer.append('p')

            #send packets in window that haven't already been sent
            if (pkt_num not in sent_packet_numbers or resend_window==True) and pkt_num<len(sender_buffer):

                #form the packet, not an ACK
                seq = create_32_bit_seq_num(False,pkt_num)
                data = sender_buffer[pkt_num]
                packet = [seq,data]

                #send packet to peer
                num_packets_sent[probe_receiver]+=1
                node_socket.sendto(str.encode(json.dumps(packet)),(receiver_ip,probe_receiver))
                
                # Start the timer if it's not already running
                if timers[probe_receiver]==0:
                    timers[probe_receiver] = time.time()

                #add sent packet with packet_num to list
                sent_packet_numbers.append(pkt_num)
          
        # waiting for ACK or timeout:
        while(timers[probe_receiver]!=0 and time.time() - timers[probe_receiver] < TIMEOUT_INTERVAL):
               pass
          
        #we have a timeout
        if timers[probe_receiver]!=0:
			# resend all packets in window, stop timer
               timers[probe_receiver]=0
               resend_window = True
        #ack was received
        else:
               resend_window = False
               #reset timer, if new first pkt in the window has already been sent
               if send_base in sent_packet_numbers:
                    timers[probe_receiver] = time.time()
          

# Also, the packet loss rate for each link should be displayed every 1 second with the following format:
# [<timestamp>] Link to <neighbor-port>: <sent-count> packets sent, <lost-count> packets lost, loss rate <loss-rate>
def packet_loss_rate_status_messages():
     global num_acks_received, num_packets_sent, sending_neighbors
     while True:
        for node in sending_neighbors:
             loss_count = num_packets_sent[node]-num_acks_received[node]
             try:
                loss_rate = round(loss_count/num_packets_sent[node],2)
             except ZeroDivisionError:
                loss_rate = 0.0

             print(f"[{get_timestamp()}] Link to {node}: {num_packets_sent[node]} packets sent, {loss_count} packets lost, lost rate {loss_rate}")
        #every second
        time.sleep(1)

def create_32_bit_seq_num(ack_flag,seqnum):
     flag_bit = 1 if ack_flag else 0
     number_bits = seqnum & 0x3FFFFFFF
     # Combine flag_bit and number_bits using bitwise OR
     result = (flag_bit << 31) | number_bits
     return result

def is_probe_packet(data):
    try:
        json.loads(data)
        return True
    except json.JSONDecodeError:
        return False

def check_rate_loss(rate_loss):
     #check for invalid rate_loss
        try:
            float(rate_loss)
        except:
             sys.exit("> [ERROR: Rate loss not a float]")

        if not 0.0<=float(rate_loss)<=1.0:
            sys.exit("> [ERROR: Rate loss needs to be between 0.0-1.0]")
        
        return float(rate_loss)

def check_port_num(port_num):
        #check for invalid port #
        try:
            int(port_num)
        except:
             sys.exit("> [ERROR: Port number not an integer]")
        if not 1024<=int(port_num)<=65535:
            sys.exit("> [ERROR: Port number out of range, needs to be in range 1024-65535]")
        
        return int(port_num)

def get_timestamp():
    timestamp = time.time()
    formatted_timestamp = f"{timestamp:.3f}"
    return formatted_timestamp

def print_routing_table():
     timestamp = get_timestamp()
     print(f"[{timestamp}] Node <port-{local_port}> Routing Table")
     for node in routing_table:
          if routing_table[node][1]!=None:
               print(f"- ({routing_table[node][0]}) Node {node}; Next hop -> Node {routing_table[node][1]}")
          else:
               print(f"- ({routing_table[node][0]}) Node {node}")

#create listing of neighbors we are receiving from
def populate_receiving_neighbors(send_index):
     global receiving_neighbors, recv_bases
     x = 3
     while(x<send_index):
        n_port = check_port_num(sys.argv[x])
        n_loss_rate = check_rate_loss(sys.argv[x+1])
        if n_port not in receiving_neighbors:
            receiving_neighbors[n_port] = n_loss_rate
        else:
            #throw error, can't use the same port twice
            sys.exit("> [ERROR: Can't have duplicate ports for receiving neighbors]")
        #populate the recv_bases for probe packets
        recv_bases[n_port] = 0
        x+=2

#create listing of neighbors we are sending to
def populate_sending_neighbors(index_of_send):
     global sending_neighbors, last_node, send_bases, num_packets_sent, num_acks_received, timers
     last_node_factor = 1 if last_node else 0
     index = index_of_send + 1
     while(index<len(sys.argv)-last_node_factor):
          n_port = check_port_num(sys.argv[index])
          if n_port not in sending_neighbors:
              #inital loss rate is 0?
              sending_neighbors[n_port] = 0
          else:
              #throw error, can't use the same port twice
              sys.exit("> [ERROR: Can't have duplicate port for sending neighbors]")
          #populate the send_bases for probe packets
          send_bases[n_port] = 0
          #total number of packets sent initially is 0
          num_packets_sent[n_port] = 0
          #total number of acks initially received is 0
          num_acks_received[n_port] = 0
          #set everyone's timer_start_time to 0
          timers[n_port] = 0

          index+=1

# cnnode <local-port> receive <neighbor1-port> <loss-rate-1> <neighbor2-port> <loss-rate-2> ... <neighborM-port>
# <loss-rate-M> send <neighbor(M+1)-port> <neighbor(M+2)-port> ... <neighborN-port> [last]
def main():
    global local_port, last_node
    #check we have the minimum amount of args >= 5
    # (program name, local port, send, receive, at least one send/receiver neighbor)
    if len(sys.argv)<5:
        sys.exit("> [ERROR: Not enough arguments]")
    
    #check the local-port #
    local_port = check_port_num(sys.argv[1])

     #check to see if last argument is last
    if(sys.argv[len(sys.argv)-1]=="last"):
        last_node = True

    #make sure that receive is the second argument
    if (sys.argv[2]!='receive'):
        sys.exit("> [ERROR: 3rd argument must be 'receive': cnnode.py <local-port> receive ...]")

    #figure out what index send is at, if it doesn't exist throw an error
    index_of_send = None
    for index, arg in enumerate(sys.argv):
         if arg == "send":
              index_of_send = index
    
    if index_of_send == None:
          sys.exit("> [ERROR: 'send' must be an argument: cnnode.py <local-port> receive .... send ....]")

    #go through the receiving_neighbors, who we are receiving from
    populate_receiving_neighbors(index_of_send)

    #go through sending_neighbors, who we are sending to
    populate_sending_neighbors(index_of_send)

    #build the initial routing table
    #distance should be zero initially
    for neighbor in receiving_neighbors:
         routing_table[neighbor] = [0, None]
    for neighbor in sending_neighbors:
         routing_table[neighbor] = [0,None]

    #print the initial routing table
    print_routing_table()


    ####
    #create the node socket
    #bind to 0.0.0.0
    node_ip = '0.0.0.0'

    #create a socket
    node_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        
    #bind to ip address & port
    # BUFFER_SIZE = 8192  # Set your preferred buffer size
    node_socket.bind((node_ip,local_port))
    # node_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, BUFFER_SIZE)

     #start receiver thread
    receiver_thread = threading.Thread(target=node_receiver, args=(node_socket,))
    receiver_thread.start()

    #if you are the last node, kick off the algorithm
    if last_node:
        update_neighbors(node_socket,True)

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