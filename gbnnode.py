import os
import sys
import socket
import threading
import json
import time

#global variables
receiver_ip = "0.0.0.0"
receiver_port = 0
sender_buffer = []
next_seq_num = 0
send_base = 0
recv_base = 0
window_size = 0
sent_buffer = []
value_of_n = 0
dropped_buffer = []
drop_option = ""
receiver_discarded = 0
receiver_total = 0
sender_discarded = 0
sender_total = 0
resend_window = False

# Set the timeout, don't start yet
TIMEOUT_INTERVAL = 0.5
timer_start_time = 0


def node_receiver(node_socket):
     #listen for incoming packets
     while(True):
          global receiver_total
          global receiver_discarded
          global timer_start_time
          #handle packet
          packet = node_socket.recvfrom(65535)
          packet = json.loads(packet[0].decode())
          pkt_num = packet[0]
          data = packet[1]

          #check to see if this an ACK or msg
          ack_bit = (pkt_num >> 31) & 1
          pkt_num = (pkt_num & 0x7FFFFFFF)
          timestamp = get_timestamp()
          
          #if message, acknowledge
          if ack_bit==0:
            #if we a deterministically dropping pkts
            if drop_option=="-d" and value_of_n != 0 and receiver_total%value_of_n==value_of_n-1:
                 print(f"[{timestamp}] packet{pkt_num} {data} discarded")
                 receiver_total+=1
                 receiver_discarded+=1
            else:
               #make sure it is not the terminator message
               if data!='\0':
                    print(f"[{timestamp}] packet{pkt_num} {data} received")
                    receiver_total+=1
                    #check if pkt is received in correct order
                    if recv_base==pkt_num:
                         #send new ack
                         ack_thread = threading.Thread(target=node_ack_sender,args=(node_socket,pkt_num,False,False))
                         ack_thread.start()
                    else:
                         #retransmit old ack
                         ack_thread = threading.Thread(target=node_ack_sender,args=(node_socket,pkt_num,True,False))
                         ack_thread.start()
               #terminator
               else:
                    #add logic to calculate summary
                    print(f"[Summary] {receiver_discarded}/{receiver_total} packets dropped, loss rate = {receiver_discarded/receiver_total}%")

                    #send terminator ack to sender
                    ack_thread = threading.Thread(target=node_ack_sender,args=(node_socket,pkt_num,False,True))
                    ack_thread.start()

                    #exit program gracefully
                    print("Exiting...")
                    os._exit(0)

          #else ack
          else:
               global send_base
               global sender_total
               global sender_discarded
               #check if we need to deterministically drop the ack
               if drop_option=="-d" and value_of_n != 0 and sender_total%value_of_n==value_of_n-1:
                    print(f"[{timestamp}] ACK{pkt_num} discarded")
                    sender_total+=1
                    sender_discarded+=1
               else:
                    #check if terminator ack
                    if data == '\0':
                         #add logic to calculate summary
                         print(f"[Summary] {sender_discarded}/{sender_total} packets discarded, loss rate = {sender_discarded/sender_total}%")
                         print("Exiting...")
                         os._exit(0)
                    else:
                         #check if duplicate ack, don't move window
                         if not pkt_num<send_base:
                              #cumulative ack
                              send_base=pkt_num+1
                              #stop timer
                              timer_start_time = 0

                         sender_total+=1
                         print(f"[{timestamp}] ACK{pkt_num} received, window moves to {send_base}")

def node_ack_sender(node_socket,pkt_num,out_of_order,is_termintor):
     timestamp = get_timestamp()
     
     #termination
     if is_termintor:
           #form the packet, is an ACK
               seq = create_32_bit_seq_num(True,pkt_num)
               data = '\0'
               packet = [seq,data]
               #send ACK
               node_socket.sendto(str.encode(json.dumps(packet)),(receiver_ip,receiver_port)) 
     else:
          #move window if not out_of_order
          if not out_of_order:
               global recv_base
               recv_base+=1
               #form the packet, is an ACK
               seq = create_32_bit_seq_num(True,pkt_num)
               data = ''
               packet = [seq,data]
               #send ACK
               node_socket.sendto(str.encode(json.dumps(packet)),(receiver_ip,receiver_port))
               print(f"[{timestamp}] ACK{pkt_num} sent, expecting packet{pkt_num+1}")   
          else:
               #form packet
               seq = create_32_bit_seq_num(True,recv_base-1)
               data = ''
               packet = [seq,data]
               #send ACK
               node_socket.sendto(str.encode(json.dumps(packet)),(receiver_ip,receiver_port))
               print(f"[{timestamp}] ACK{recv_base-1} sent, expecting packet{recv_base}")  

     
def node_sender(node_socket,message):
     global send_base
     global sent_buffer
     global timer_start_time
     global resend_window
     
     #add each char to buffer
     for x in message:
          sender_buffer.append(x)

     #check to see if we can send anything in the window from the buffer
     #continuous loop through
     while (True):
          
          for pkt_num in range(send_base,window_size+send_base):
               #send packets in window that haven't already been sent
               if (pkt_num not in sent_buffer or resend_window==True) and pkt_num<len(sender_buffer):

                    #form the packet, not an ACK
                    seq = create_32_bit_seq_num(False,pkt_num)
                    data = sender_buffer[pkt_num]
                    packet = [seq,data]

                    #check if we have reached the terminator char & the rest of the packets have been acked
                    if sender_buffer[pkt_num]=='\0' and send_base==pkt_num:
                         #send packet to peer
                         node_socket.sendto(str.encode(json.dumps(packet)),(receiver_ip,receiver_port))
                         #add sent packet with packet_num to list
                         sent_buffer.append(pkt_num)

                    elif sender_buffer[pkt_num]!='\0':
                         #send packet to peer
                         timestamp = get_timestamp()
                         node_socket.sendto(str.encode(json.dumps(packet)),(receiver_ip,receiver_port))
                         print(f"[{timestamp}] packet{pkt_num} {data} sent")

                         # Start the timer if it's not already running
                         if timer_start_time==0:
                              timer_start_time = time.time()
                         
                         #add sent packet with packet_num to list
                         sent_buffer.append(pkt_num)
                    
          #while waiting for ACK or timeout:
          while(timer_start_time!=0 and time.time() - timer_start_time < TIMEOUT_INTERVAL):
               pass
          
          #we have a timeout
          if timer_start_time!=0:
			# timeout announcement
               print(f"[{get_timestamp()}] packet{send_base} timeout")
			# resend all packets in window, stop timer
               timer_start_time=0
               resend_window = True
          #ack was received
          else:
               resend_window = False
               #reset timer, if new first pkt in the window has already been sent
               if send_base in sent_buffer:
                    timer_start_time = time.time()

def create_32_bit_seq_num(ack_flag,seqnum):
     flag_bit = 1 if ack_flag else 0
     number_bits = seqnum & 0x3FFFFFFF
     # Combine flag_bit and number_bits using bitwise OR
     result = (flag_bit << 31) | number_bits
     return result

def get_timestamp():
    timestamp = time.time()
    formatted_timestamp = f"{timestamp:.3f}"
    return formatted_timestamp

def check_port_num(port_num):
        #invalid port #
        try:
            int(port_num)
        except:
             sys.exit("> [ERROR: Port number not an integer]")
        if not 1024<=int(port_num)<=65535:
            sys.exit("> [ERROR: Port number out of range, needs to be in range 1024-65535]")
        
        return int(port_num)

 #python gbnnode.py <self-port> <peer-port> <window-size> [ -d <value-of-n> | -p <value-of-p>]
def main():
   
    #check correct number of args
    if len(sys.argv)!=6:
        sys.exit("> [ERROR: Incorrect number of arguments]")
    
    #check the port numbers
    self_port = check_port_num(sys.argv[1])
    global receiver_port
    receiver_port = check_port_num(sys.argv[2])

    #check window size
    try:
         global window_size
         window_size = int(sys.argv[3])
    except:
         sys.exit("> [ERROR: Invalid window-size, needs to be an integer]")
    
    #check option for dropping packets
    if sys.argv[4]=="-d" or sys.argv[4]=="-p":
        global drop_option
        drop_option = sys.argv[4]
        #make sure n is an int
        if drop_option=='-d':
            try:
                global value_of_n
                value_of_n = int(sys.argv[5])
            except: 
                    sys.exit("> [ERROR: value-of-n must be an int]")
        #make sure value of p is between 0 and 1
        else:
             try:
                   value_of_p = float(sys.argv[5])
             except:
                   sys.exit("> [ERROR: value-of-p must be between 0 and 1]")

             if not 0<=value_of_p<=1:
                    sys.exit("> [ERROR: value-of-p must be between 0 and 1]") 
    else:
         sys.exit("> [ERROR: invalid option for dropping packets, must be -d or -p]")
    

    ##########
    #bind to 0.0.0.0
    node_ip = '0.0.0.0'

    #create a socket
    node_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        
    #bind to ip address & port
    node_socket.bind((node_ip,self_port))

    #start receiver thread
    receiver_thread = threading.Thread(target=node_receiver, args=(node_socket,))
    receiver_thread.start()

    #send messages
    while(True):
         try:
            message = input("node> ")

            #check that the message starts with send, else invalid command
            if message.startswith('send '):
                #add terminator to string
                message = message.split("send ")[1]+'\0'
                #create thread to handle sending of message
                send_thread = threading.Thread(target=node_sender,args=(node_socket,message))
                send_thread.start()
            else:
                 print("[ERROR: Invalid command]")

         except KeyboardInterrupt:
              #handle Ctrl+C
              print("> Exiting...")
              os._exit(0)



#run main
if __name__ == "__main__":
    main()