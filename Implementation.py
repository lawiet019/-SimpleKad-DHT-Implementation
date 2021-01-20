from concurrent import futures
import time
import math

import grpc

import csci4220_hw3_pb2
import csci4220_hw3_pb2_grpc
from collections import OrderedDict
from collections import deque

class KadImplServicer(csci4220_hw3_pb2_grpc.KadImplServicer):
    def __init__(self, id, port, address, k):
        # init variable from the parameters
        self.id = id
        self.port = port
        self.address = address
        self.k = k
        self.k_bucket = [OrderedDict(),OrderedDict(),OrderedDict(),OrderedDict()]
        self.library = {}



    def  print_k_bucket(self):
        for i in range(4):
            prt_str = ""
            prt_str = str(i)+":"
            for k in self.k_bucket[i]:
                v = self.k_bucket[i][k]
                prt_str+= " "+ str(v.id)+ ":" + str(v.port)
            print(prt_str)
    def compute_dist(self,key1,key2):
        xor_v = key1 ^ key2
        dist  = len(bin(xor_v))
        return dist -2

    def find_nearest_k(self,key,k,filter = []):
        res = {}
        lst = []
        cur_node = csci4220_hw3_pb2.Node(id=self.id,port=int(self.port),address=self.address)
        lst.append((cur_node,self.compute_dist(self.id,key)))
        for i in range(4):
            for k_i in self.k_bucket[i]:
                v = self.k_bucket[i][k_i]
                lst.append((v,self.compute_dist(v.id,key)))
        sorted_lst = sorted(lst,key= lambda x:(x[1],x[0].id^key))
        nodes = [i[0] for i in sorted_lst if not i[0].id in filter]
        return nodes[:k]

    def broadcast(self,remote_hostname,remote_port):
    	with grpc.insecure_channel(remote_hostname+":"+str(remote_port)) as channel:
            stub  =  csci4220_hw3_pb2_grpc.KadImplStub(channel)
            cur_node = csci4220_hw3_pb2.Node(id=self.id,port=int(self.port),address=self.address)
            IDKey = csci4220_hw3_pb2.IDKey(node = cur_node,idkey= self.id)
            # run the remote FindNode
            res = stub.FindNode(IDKey)
            #update the k_bucket
            self.update_k_bucket(res.responding_node)
            for new_node in res.nodes:
                self.update_k_bucket(new_node)
            #print k_bucket
            print("After BOOTSTRAP(%d), k_buckets now look like:"%res.responding_node.id)
            self.print_k_bucket()


    def update_k_bucket(self,new_node):
        # calculate the index of the bucket to store the node
        xor_v = self.id ^ new_node.id
        i = len(bin(xor_v)) -3
        # put the node into bucket
        if len(self.k_bucket[i]) >= self.k:
            if new_node.id in self.k_bucket[i]:
                del self.k_bucket[i][new_node.id]
            else:
                self.k_bucket[i].popitem(last = False)
        self.k_bucket[i][new_node.id] = new_node
    def handle_find_node(self,node_id):
        # if the finding node is this node
        finded_node =None
        if self.id ==node_id:
            return True
        else:
            flag = False
            visited = {self.id}
            k_nodes = deque(self.find_nearest_k(node_id,self.k))
            while k_nodes:
                node = k_nodes.popleft()

                if not node.id in visited:
                    self.update_k_bucket(node)
                    if node.id == node_id:
                        flag = True
                        break;
                    with grpc.insecure_channel(node.address+":"+str(node.port)) as channel:
                        stub  =  csci4220_hw3_pb2_grpc.KadImplStub(channel)
                        cur_node = csci4220_hw3_pb2.Node(id=self.id,port=int(self.port),address=self.address)
                        IDKey = csci4220_hw3_pb2.IDKey(node=cur_node,idkey= node_id)
                        res = stub.FindNode(IDKey)
                        visited.add(node.id)
                        for n in res.nodes:
                            if not n.id in visited:
                                k_nodes.append(n)
            while k_nodes:
                node = k_nodes.popleft()
                self.update_k_bucket(node)

            return flag





    def handle_find_value(self,key):
        #reserve the visited node id
        if key in self.library:
            print("Found data \"%s\" for key %d"%(self.library[key],key))
            return

        visited = set()
        visited.add(self.id)
        k_nodes = deque(self.find_nearest_k(key,self.k))


        # change to while with pop
        while k_nodes:
            node = k_nodes.popleft()
            if not  node.id in visited:
                with grpc.insecure_channel(node.address+":"+str(node.port)) as channel:
                    stub  =  csci4220_hw3_pb2_grpc.KadImplStub(channel)
                    cur_node = csci4220_hw3_pb2.Node(id=self.id,port=int(self.port),address=self.address)
                    IDKey = csci4220_hw3_pb2.IDKey(node=cur_node,idkey= key)
                    res = stub.FindValue(IDKey)
                    visited.add(node.id)
                    # contain key value or nodes
                    if res.mode_kv:
                        print("Found value \"%s\" for key %d"%(res.kv.value,key))
                        if res.responding_node!=self.id:
                            self.update_k_bucket(node)
                        return
                    else:
                        for n in res.nodes:
                            if not n.id in visited:
                                k_nodes.append(n)
        print("Could not find key %d"%(key))


    def handle_store(self,key,value):
        near_point = self.find_nearest_k(key,1)[0]
        if near_point.id == self.id:
            self.library[key] = value
            print("Storing key %d at node %d"%(key,self.id))
        else:
            with grpc.insecure_channel(near_point.address+":"+str(near_point.port)) as channel:
                stub  =  csci4220_hw3_pb2_grpc.KadImplStub(channel)
                cur_node = csci4220_hw3_pb2.Node(id=self.id,port=int(self.port),address=self.address)
                kv = csci4220_hw3_pb2.KeyValue(node = cur_node,key = key,value = value)
                print("Storing key %d at node %d"%(key,near_point.id))
                res = stub.Store(kv)

    def handle_quit(self):
        for i in range(4):
            for k in self.k_bucket[i]:
                v = self.k_bucket[i][k]
                print("Letting %d know I'm quitting."%(v.id))
                try:
                    with grpc.insecure_channel(v.address+":"+str(v.port)) as channel:
                        stub  =  csci4220_hw3_pb2_grpc.KadImplStub(channel)
                        cur_node = csci4220_hw3_pb2.Node(id=self.id,port=int(self.port),address=self.address)
                        IDKey = csci4220_hw3_pb2.IDKey(node = cur_node,idkey= self.id)
                        stub.Quit(IDKey)
                except Exception as e:
                    pass;

        print("Shut down node %d"%self.id)


    # function to be implemented
    def FindNode(self, request, context):
        print("Serving FindNode(%d) request for %d"%(request.idkey,request.node.id))
        #update key buckets:
        if self.id !=request.node.id:
            i = self.compute_dist(self.id,request.node.id) -1
            self.k_bucket[i][request.node.id] = request.node
        k_nodes = self.find_nearest_k(request.idkey,self.k,[request.node.id,self.id])
        cur_node = csci4220_hw3_pb2.Node(id=self.id,port=int(self.port),address=self.address)

        nl = csci4220_hw3_pb2.NodeList(responding_node = cur_node,nodes = k_nodes)
        return nl
    def FindValue(self, request, context):
        print("Serving FindKey(%d) request for %d"%(request.idkey,request.node.id))
        key = request.idkey
        if self.id !=request.node.id:
            self.update_k_bucket(request.node)
        if key in self.library:
            cur_node = csci4220_hw3_pb2.Node(id=self.id,port=int(self.port),address=self.address)
            key_value = csci4220_hw3_pb2.KeyValue(node = cur_node,key=key,value = self.library[key])
            kv_wrapper = csci4220_hw3_pb2.KV_Node_Wrapper(responding_node = cur_node,mode_kv=1,kv=key_value,nodes=[])
            return kv_wrapper
        else:
            cur_node = csci4220_hw3_pb2.Node(id=self.id,port=int(self.port),address=self.address)
            k_nodes = self.find_nearest_k(request.idkey,self.k)
            kv_wrapper = csci4220_hw3_pb2.KV_Node_Wrapper(responding_node = cur_node,mode_kv=0,kv=None,nodes=k_nodes)
            return kv_wrapper


    def Store(self, request, context):
        print("Storing key %d value \"%s\""%(request.key,request.value))
        self.library[request.key] = request.value
        cur_node = csci4220_hw3_pb2.Node(id=self.id,port=int(self.port),address=self.address)
        IDKey = csci4220_hw3_pb2.IDKey(node=cur_node,idkey= request.key)
        return IDKey

    def Quit(self, request, context):
        quit_id = request.idkey
        i = self.compute_dist(self.id,quit_id) -1
        flag = True
        if quit_id in self.k_bucket[i]:
            del self.k_bucket[i][quit_id]
            print("Evicting quitting node %d from bucket %i"%(quit_id,i))
        else:
            print("No record of quitting node %d in k-buckets."%quit_id)
        cur_node = csci4220_hw3_pb2.Node(id=self.id,port=int(self.port),address=self.address)
        IDKey = csci4220_hw3_pb2.IDKey(node=cur_node,idkey= quit_id)
        return IDKey
