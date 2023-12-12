import sys

#GLOBALS
local_port = 0
last_node = False
#nodes we are receiving from
receiving_neighbors = {}
#nodes we are sending to
sending_neighbors = {}

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

#create listing of neighbors we are receiving from
def populate_receiving_neighbors(send_index):
     global receiving_neighbors
     x = 3
     while(x<send_index):
        n_port = check_port_num(sys.argv[x])
        n_loss_rate = check_rate_loss(sys.argv[x+1])
        if n_port not in receiving_neighbors:
            receiving_neighbors[n_port] = n_loss_rate
        else:
            #throw error, can't use the same port twice
            sys.exit("> [ERROR: Can't have duplicate ports for receiving neighbors]")
        x+=2

#create listing of neighbors we are sending to
def populate_sending_neighbors(index_of_send):
     global sending_neighbors, last_node
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
          index+=1

# cnnode <local-port> receive <neighbor1-port> <loss-rate-1> <neighbor2-port> <loss-rate-2> ... <neighborM-port>
# <loss-rate-M> send <neighbor(M+1)-port> <neighbor(M+2)-port> ... <neighborN-port> [last]
def main():
    global local_port, last_node
    #check we have the minimum amount of args >= 6
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
    print(receiving_neighbors)

    #go through sending_neighbors, who we are sending to
    populate_sending_neighbors(index_of_send)
    print(sending_neighbors)

#run main
if __name__ == "__main__":
    main()