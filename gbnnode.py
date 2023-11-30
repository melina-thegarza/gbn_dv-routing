
import os
import sys
import socket
import threading

def node_receiver(node_socket):
     #listen for incoming packets
     while(True):
          packet = node_socket.recvfrom(65535)
          print(packet)

     
     

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
    peer_port = check_port_num(sys.argv[2])

    #check window size
    try:
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
            #create thread to handle sending of message

         except KeyboardInterrupt:
              #handle Ctrl+C
              print("> Exiting...")
              os._exit(0)



#run main
if __name__ == "__main__":
    main()