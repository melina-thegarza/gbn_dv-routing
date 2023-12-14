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

## OVERVIEW OF FUNCTIONS IMPLEMENTED

## OVERVIEW OF DATA STRUCTURES USED
