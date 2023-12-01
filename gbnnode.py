
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

def node_receiver(node_socket):
     #listen for incoming packets
     while(True):
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
            print(f"[{timestamp}] packet{pkt_num} {data} received")
            #send ack
            ack_thread = threading.Thread(target=node_ack_sender,args=(node_socket,pkt_num))
            ack_thread.start()
          #else ack, move window
          else:
               global send_base
               send_base+=1
               print(f"[{timestamp}] ACK{pkt_num} received, window moves to {send_base}")

               #check to see if we can send another packet
               sender_thread = threading.Thread(target=node_sender,args=(node_socket,''))
               sender_thread.start()

def node_ack_sender(node_socket,pkt_num):
     timestamp = get_timestamp()
     #move window
     global recv_base
     recv_base+=1

     #form the packet, is an ACK
     seq = create_32_bit_seq_num(True,pkt_num)
     data = ''
     packet = [seq,data]

     #send ACK
     node_socket.sendto(str.encode(json.dumps(packet)),(receiver_ip,receiver_port))
     print(f"[{timestamp}] ACK{pkt_num} sent, expecting packet{recv_base}")          

     
def node_sender(node_socket,message):
     global send_base
     
     #add each char to buffer
     for x in message:
          sender_buffer.append(x)

     #check to see if we can send anything in the window from the buffer
    #  print(f"this is my buffer: {sender_buffer}")
     for pkt_num in range(send_base,window_size+send_base):
          if pkt_num not in sent_buffer and pkt_num<len(sender_buffer):
       
               #form the packet, not an ACK
               seq = create_32_bit_seq_num(False,pkt_num)
               data = sender_buffer[pkt_num]
               packet = [seq,data]

               #send packets to peer
               timestamp = get_timestamp()
               node_socket.sendto(str.encode(json.dumps(packet)),(receiver_ip,receiver_port))
               print(f"[{timestamp}] packet{pkt_num} {data} sent")
               
              
               #add sent packet with packet_num to list
               sent_buffer.append(pkt_num)

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
        drop_option = sys.argv[4]
        #make sure n is an int
        if drop_option=='-d':
            try:
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
                #create thread to handle sending of message
                send_thread = threading.Thread(target=node_sender,args=(node_socket,message.split("send ")[1]))
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