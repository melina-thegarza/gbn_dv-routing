Programming Assignment 2: Network Protocols Emulation
Name: Melina Garza Uni: mjg2290


## DESCRIPTION
    Implemented a program that simulates a node in a computer network. The program incorporates a Go-Back-N Protocol for ensuring reliable transmissions at the Transport Layer and a Distance-Vector Routing Algorithm to achieve efficient routing at the Network Layer. As an independent node, the program emulates the interaction between multiple nodes, enabling them to send packets to each other as if connected by links. 


## COMMANDS NEEDED TO RUN THE PROGRAM

	# Go-Back-N Protocol

		python3 gbnnode.py <self-port> <peer-port> <window-size> [ -d <value-of-n> | -p <value-of-p>]
	
		examples:
			'python3 gbnnode.py 2222 1111 3 -p .25'
			'python3 gbnnode.py 1111 2222 3 -d 4'


	# Distance-Vector Routing Algorithm
		python dvnode.py <local-port> <neighbor1-port> <loss-rate-1> <neighbor2-port> <loss-rate-2> ... [last]
		
		examples:
			'python3 dvnode.py 1111 2222 .1'
			'python3 dvnode.py 3333 2222 .2 last'
	
	# Combination

		python3 cnnode.py <local-port> receive <neighbor1-port> <loss-rate-1> <neighbor2-port> <loss-rate-2> ... <neighborM-port><loss-rate-M> send <neighbor(M+1)-port> <neighbor(M+2)-port> ... <neighborN-port> [last]

		examples:
			'python3 cnnode.py 1111 receive send 2222 3333'
			'python3 cnnode.py 4444 receive 2222 .8 3333 .5 send last'

## PACKET STRUCTURE

	# Go-Back-N Protocol
		packet = 5 bytes total
			packet header = 4 bytes -> 32 bit sequence #, 31st bit determines whether ACK(=1) or Message(=0), 30th-0th is the packet sequence number
			data = 1 byte
	# Distance-Vector Routing Algorithm
		packet = f"{local_port} {json.dumps(routing_table)}"
	# Combination
		probe packets = same as GBN packet but data is a const char = 'p'

## OVERVIEW OF FUNCTIONS IMPLEMENTED
	# Used by all
		# create_32_bit_seq_num(ack_flag,seqnum) -> creates the packet header which includes a flag to determine if it is an ACK or Messsage, & the packet sequence number
		# get_timestamp() -> used to get a nicely formatted timestamp, down to the millisecond
		# check_port_num(port_num) -> ensures that our port numbers are valid and returns the port_num as an int
		
	# Go-Back-N Protocol
		# node_receiver(node_socket) -> this thread that handles all incoming packets(Messages & ACKs), also performs probabilistic and deterministic dropping of the packets
		# node_ack_sender(node_socket,pkt_num,out_of_order,is_terminator) -> handles the sending of ACKS back to the sender
		# node_sender(node_socket,message) -> this thread handles the sending of messages(Non-ACK packets) to the receiver, implements the timeout & resends the entire window if we encounter a timeout
		
	# Distance-Vector Routing Algorithm
		# node_receiver(node_socket) -> this thread handles all DV updates from its neighbors, creates a separate thread to handle the processing of the sent DV routing table
		# receive_routing_table(sender_port,sender_routing_table, node_socket) -> uses the Bellman-Ford algorithm to update local routing table based on sender's routing table, if updates are made it triggers update_neighbors()
		# update_neighbors(node_socket) -> when there is a change in the local DV routing table, sends routing table to neighbors
	
	# Combination
		# every_5_seconds_update(node_socket) ->  updates of routing table should only be sent out every 5 seconds, if there's any change in the rounded distances based on the newly calculated loss rate
		# node_receiver(node_socket) -> uses ThreadPoolExecutor for handling incoming packets, we have a pool of max 10 threads that are processing the packets
		# process_packet(node_socket,packet) -> differentiates between receiving DV updates and receiving probe packets, triggers respective threads to handle the packet correctly
		# handle_probe_packet(node_socket, probe_sender, packet) -> as the probe receiver I drop the packets based on the probabilistic drop value & as the probe sender I never drop any ACKs
		# receive_routing_table(sender_port,sender_routing_table, node_socket) -> similar to part 3's implementation, major differences include how it handles receiving a direct link cost update from a probe sender and being more cautious about paths with next-hops
		# probe_sender(node_socket, probe_receiver) -> a thread for each node we are sending to is created: this function is responsible for continuously sending probe packets to the probe receiver & follows similar logic to the node_sender in the GBN protocol, except that certain things are pre-set such as window size
		# packet_loss_rate_status_messages() -> handles displaying the packet loss rate for each link every 1 second

## OVERVIEW OF DATA STRUCTURES USED
	# Go-Back-N Protocol
		# sender_buffer -> buffer[list] that all data packets are put in before being sent out
		# sent_packet_numbers -> list that keeps track of the packets we have already sent
		
	# Distance-Vector Routing Algorithm
		# neighbors -> global dictionary that holds each neighbor's info, format: {neighbor-port-#: loss-rate/distance}, used in the DV algorithm
		# routing_table -> global dictionary that keeps track of the node's local_routing_table, format: {neighbor-port-#: [loss-rate/distance, next-hop]}
	
	# Combination
		# timers -> global dictionary that holds a timer for each probe receiver, used for timeout calculations for sending probe packets
		# num_packets_sent -> global dictionary that keeps track, on the sender side of the total amount of packets sent to each probe receiver, format: {neighbor-port-#: packets_sent}
		# num_acks_received -> global dictionary that keeps track, on the sender side of the total amount of ACKS received from each probe receiver, format: {neighbor-port-#: acks_received}
		# recv_bases -> global dictionary that keeps track of our various recv_bases for the different links, format: {neighbor-port-#: recv_base_#}
		# send_bases -> global dictionary that keeps track of our various send_bases for the different links, format: {neighbor-port-#: send_base_#}
