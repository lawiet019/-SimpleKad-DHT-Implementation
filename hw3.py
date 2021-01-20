#!/usr/bin/env python3

from concurrent import futures
import sys  # For sys.argv, sys.exit()
import socket  # for gethostbyname()

import grpc

import csci4220_hw3_pb2
import csci4220_hw3_pb2_grpc

from Implementation import KadImplServicer








def run():
	if len(sys.argv) != 4:
		print("Error, correct usage is {} [my id] [my port] [k]".format(sys.argv[0]))
		sys.exit(-1)

	id = int(sys.argv[1])
	port = sys.argv[2] # add_insecure_port() will want a string
	k = int(sys.argv[3])
	hostname = socket.gethostname() # Gets my host name
	address = socket.gethostbyname(hostname) # Gets my IP address from my hostname

	# init the basic info of  node
	node = KadImplServicer(id,port,address,k)
	#init the gRPC server
	server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
	csci4220_hw3_pb2_grpc.add_KadImplServicer_to_server(node, server)
	server.add_insecure_port('[::]:'+ port)
	server.start()



	while True:
		commands = input()
		commands_list = commands.split()
		command = commands_list[0]
		if command == 'BOOTSTRAP':
			remote_hostname = commands_list[1]
			remote_port = int(commands_list[2])
			node.broadcast(remote_hostname,remote_port)

		elif command == 'FIND_NODE':
			node_id = int(commands_list[1])
			print("Before FIND_NODE command, k-buckets are:")
			node.print_k_bucket()
			flag = node.handle_find_node(node_id)
			if flag:
				print("Found destination id %d"%(node_id))
			else:
				print("Could not find destination id %d"%(node_id))
			print("After FIND_NODE command, k-buckets are:")
			node.print_k_bucket()



		elif command == 'FIND_VALUE':
			key = int(commands_list[1])
			print("Before FIND_VALUE command, k-buckets are:")
			node.print_k_bucket()
			node.handle_find_value(key)
			print("After FIND_VALUE command, k-buckets are:")
			node.print_k_bucket()




		elif command == 'STORE':
			key = int(commands_list[1])
			value = commands_list[2]
			node.handle_store(key,value)


		elif command == 'QUIT':

			node.handle_quit()
			break;


		else:
			print("you format of command is not correct")







	''' Use the following code to convert a hostname to an IP and start a channel
	Note that every stub needs a channel attached to it
	When you are done with a channel you should call .close() on the channel.
	Submitty may kill your program if you have too many file descriptors open
	at the same time. '''

	#remote_addr = socket.gethostbyname(remote_addr_string)
	#remote_port = int(remote_port_string)
	#channel = grpc.insecure_channel(remote_addr + ':' + str(remote_port))

if __name__ == '__main__':
	run()
