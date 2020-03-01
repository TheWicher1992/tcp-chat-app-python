'''
This module defines the behaviour of a client in your Chat Application
'''
import sys
import getopt
import socket
import random
from threading import Thread
import os
import util
import time
import math
import queue


'''
Write your code inside this class. 
In the start() function, you will read user-input and act accordingly.
receive_handler() function is running another thread and you have to listen 
for incoming messages in this function.
'''

class Client:
    '''
    This is the main Client Class. 
    '''
    def __init__(self, username, dest, port, window_size):
        self.server_addr = dest
        self.server_port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(None)
        self.sock.bind(('', random.randint(10000, 40000)))
        self.name = username
        self.packet_queue = queue.Queue(1)
        self.packet_buff = {}
        self.packet_history = {}
        self.ack_buffer = -1
        self.ack_queue = queue.Queue()
        
        self.packet_num = -1
        self.window = window_size

    '''
        sort the packets using their sequence numbers.
        then check which seqno is missing.
        send ack packet for that seqno
    '''
    def send_ack(self,packet):
        packets = self.packet_buff
        packets = sorted(packets.keys())       
        for n in packets:
            if int(n)+1 not in packets:
                ack = util.make_packet("ack",int(n)+1,"")
                self.send_req(ack)
                break

    def getPacketsFromBuffer(self):
        '''
         sort the packets in the buffer to counter out of order packets.
         append the sorted packets to the packet array and return it
        '''
        packets = []
        for u in sorted(self.packet_buff.keys()):
            packets.append(self.packet_buff[u])

        return packets

    def construct_message(self,all_packets):
        '''
         leave out end and start packets and make complete message from the packets recieved
        '''
        packets_to_use = len(all_packets) - 1
        msg = ""
        for i in range(1,packets_to_use):
            p_type,seqno,data,checksum = util.parse_packet(all_packets[i])
            msg = msg + data

        return msg

    def resetBuffer(self):
        #just empty the buffer
        self.packet_buff = {}     
    
    def incrementPacketn(self):
        #increment the seqno of the packe to be sent
        self.packet_num = self.packet_num+1

    def waitAndreSend(self,packet):
        '''
         in the case of single packet transmission, send the packet and then wait for its acknowledgemtn
         if the ack is recieved within 0.5 ms then good, otherwise resend packer

         '''
        sent = False
        resend = 5
        while sent == False and resend>0:
            try:
                ack = self.ack_queue.get(timeout=0.5)
                sent = True
            except:
                self.send_req(packet)
                resend = resend - 1
           

    def reset_ack_queue(self):
        #empty out the ack buffer
        while not self.ack_queue.empty():
            self.ack_queue.get()

    def start_conn(self):
        #sends the start packet and waits till the connection is established
        self.incrementPacketn()
        start = util.make_packet("start",self.packet_num,"")
        self.send_req(start)
        self.waitAndreSend(start)
        self.reset_ack_queue()
    
    def end_conn(self):
        #sends the end packet to mark the end of transmission
        self.reset_ack_queue()
        self.incrementPacketn()
        end = util.make_packet("end",self.packet_num,"")
        self.send_req(end)
        self.waitAndreSend(end)
        self.reset_ack_queue()


    def send_tcp(self,req):
        #if packet to be sent is only 1, this functoins sends and waits
        self.start_conn()
        self.incrementPacketn()
        packet = util.make_packet("data",self.packet_num,req)
        self.send_req(packet)
        self.waitAndreSend(packet)
        self.end_conn()


    def send_window_tcp(self,chunks):
        self.start_conn()
       
        b = 0
        w = self.window
        sent = False
        seqno = self.packet_num + 1
        packet_history = []  
        # make packet from every chunk
        for i in range(0,len(chunks)):
            self.incrementPacketn()
            chunks[i] = util.make_packet("data",self.packet_num,chunks[i])   
        
        to_send = 0
        t_time = 0

        # loop until all packets are sent
        while b < len(chunks):
            #send packets if the window is available
            while to_send < b + w and to_send < len(chunks):
                
                packet = chunks[to_send]
                packet_history.append(packet)
                self.send_req(packet)
                to_send = to_send + 1  
            try:
                #wait for the ack, if ack is received then slide window
                #else dont slide the window

                tmp = self.ack_queue.get(timeout=0.5)
                num_of_pckt_rcvd = int(tmp) - seqno    
                if num_of_pckt_rcvd > 0:
                    b=b+1
                    seqno = seqno + num_of_pckt_rcvd            
            except:
                #if ack not received resend the window
                to_send = b


        self.end_conn()


    def join(self):
        '''
         makes the join request
        '''
        req = ""
        self.start_conn()

        join_req = util.make_message("join",1,self.name)
        self.incrementPacketn()
        packet = util.make_packet('data',self.packet_num,join_req)
        self.send_req(packet)  
        self.waitAndreSend(packet)

        self.end_conn()
        

    def extract_message(self,cmd):

        '''
         provided with the user input the function returns a constructed message
        '''
        to_clients = ""
        no_clients = cmd[1]
        no_clients = int(no_clients)
        for i in range(2,no_clients+2):
            to_clients = to_clients + cmd[i] + " "

        to_clients = to_clients.strip()
        
        msg_to_send = ""
        for i in range(no_clients+2,len(cmd)):
            msg_to_send = msg_to_send + cmd[i] + " "
    
        msg_to_send = msg_to_send.strip()
    
        tmp = str(no_clients) + " " + to_clients + " " + msg_to_send
        tmp = tmp.strip()
        return tmp

    def extract_file(self,cmd):
        # provided with the user input,
        # function reads the file constructs a message and returns it
        to_clients = ""
        no_clients = cmd[1]
        no_clients = int(no_clients)

        for i in range(2,no_clients+2):
            to_clients = to_clients + cmd[i] + " "

        to_clients = to_clients.strip()
        file_name = cmd[len(cmd)-1]
        try:
            f = open(file_name,'r')
            file_data = f.read()
            tmp = str(no_clients) + " " + to_clients + " " + file_name + " <delimtter>" + file_data

            # packet = util.make_packet("data",0,req)
        
            f.close()
            return tmp
        except:
            print("file not found")

        


    def start(self):
        '''
        Main Loop is here   
        Start by sending the server a JOIN message.
        Waits for userinput and then process it
        '''
       
        
      
        
        
        #joins the server      
        self.join()
      
      
        # handle commands in this loop
        while True:
            cmd = input()
            cmd = cmd.split()
            cmd_type = cmd[0]
            
            if cmd_type == "list":
                            
                req = util.make_message("request_users_list",2)
                self.send_tcp(req)
               
               
            elif cmd_type == "quit":
            
                req = util.make_message("disconnect",1,self.name)
                self.send_tcp(req)
                
                print("quitting")
                sys.exit()
            
            elif cmd_type == "msg":

                try:
                    tmp = self.extract_message(cmd)
                    req = util.make_message("send_message",4,tmp)
                    chunks = []
                    #if the length is less than 1400 just send the packet
                    if len(req) <= 1400:

                        self.send_tcp(req)
                        
                    else:
                        # make chunks of size 1400
                        size = 1400

                        numberOfPackets = int(len(req)/size)+1
                        #slice the message in 1400 packets
                        for i in range(0,numberOfPackets):
                            chunks.append(req[i*size:(i+1)*size])
                        
                        tmp_str = ""                 
                        tmp_str = chunks[0]
                        tmp_str = tmp_str[18:]
                        chunks[0] = util.make_message("send_message",4,tmp_str)
                        #call the send window function
                        self.send_window_tcp(chunks)
                except:
                    print("arguments to \"msg\" are incomplete")
                    print("enter \"help\"")
                    
                
            elif cmd_type == "file":

                try:
                    tmp = self.extract_file(cmd)
                    req = util.make_message("send_file",4,tmp)
                    chunks = []
                    #if the length is less than 1400 just send the packet

                    if len(req) <= 1400:
                        self.send_tcp(req)
                        
                    else:
                        size = 1400
                        # make chunks of size 1400

                        numberOfPackets = int(len(req)/size) +1
                        #slice the message in 1400 packets

                        for i in range(0,numberOfPackets):
                            chunks.append(req[i*size:(i+1)*size])

                        tmp_str = ""                 
                        tmp_str = chunks[0]
                        tmp_str = tmp_str[15:]
                        chunks[0] = util.make_message("send_file",4,tmp_str)
                        #call the send window function
                       
                        self.send_window_tcp(chunks)
                except:
                    print("arguments to \"file\" incomplete")
                    print("enter \"help\"")



            elif cmd_type == "help":
                print("Message:\nFormat: msg <number_of_users> <username1> <username2> ... <message>")
                print("------------------------------------------------------------------------------")
                print("File:\nFormat: file <number_of_users> <username1> <username2> ... <file_name>")
                print("------------------------------------------------------------------------------")
                print("Available Users:\nInput: list")
                print("------------------------------------------------------------------------------")
                print("Quit:\nInput: quit")
                print("------------------------------------------------------------------------------")
                print("Help:\nInput: help")
                print("------------------------------------------------------------------------------")
            else:
                print("incorrect userinput format")
                print("enter \"help\"")

            
            
    def send_req(self,req):
        self.sock.sendto(req.encode("utf-8"),(self.server_addr,self.server_port))



    def receive_handler(self):
        '''
        Waits for a message from server and process it accordingly
        '''
       
        while True:
            start = False
            end = False

            # loop from start packet to end packet
            while(start == False or end == False):
                packet = self.sock.recv(4096)
                p_type,seqno,res,checksum = util.parse_packet(packet.decode("utf-8"))
                if(p_type=="ack"):   # store ack in ack buffer
                    self.ack_buffer = int(seqno)
                    self.ack_queue.put(int(seqno),block=True)
                if p_type != "ack": # if not ack buffer the packer
                    self.packet_buff[int(seqno)] = packet.decode("utf-8")
                if p_type == "start":
                    start = True
                if p_type == "end":
                    end = True
                if p_type  !="ack":  #send ack for every packet received
                    self.send_ack(packet)
            
            
            #get packets from buffer
            all_packets = self.getPacketsFromBuffer()

            # construct full message frm the packets
            res = self.construct_message(all_packets)
         


            #process data here
            res_unsplit = res
            res = res.split()
            res_type = res[0]

            # max number of client reached
            if res_type == "err_server_full":
            # print("disconnected: server full")
                os._exit(1)
            # username is already taken or unavailable
            elif res_type == "err_username_unavailable":
            # print("disconnected: username not available")
                os._exit(1)
            elif res_type == "response_users_list":
                total_clients = res[2]
                total_clients = int(total_clients)
                out = "list:"
                for i in range(3,total_clients+3):
                    out = out + " " + res[i]
                print(out)
            elif res_type == "forward_message":
                sender = res[3]
                recieved_text = ''
                for i in range(4,len(res)):
                    recieved_text = recieved_text + " " + res[i]
                recieved_text = recieved_text.strip()

                print("msg:",sender +":",recieved_text)
            elif res_type == "forward_file":
                sender = res[3]
                file_recieved = res[4]

                d = res_unsplit.split("<delimtter>")
                text = d[1]
                print("file:",sender+":",file_recieved)
                f = open(self.name+"_"+file_recieved,'w')
                f.write(text)
                f.close()
            elif res_type == "err_unknown_message":
                os._exit(1)
            self.resetBuffer()
            self.reset_ack_queue()




               






# Do not change this part of code
if __name__ == "__main__":
    def helper():
        '''
        This function is just for the sake of our Client module completion
        '''
        print("Client")
        print("-u username | --user=username The username of Client")
        print("-p PORT | --port=PORT The server port, defaults to 15000")
        print("-a ADDRESS | --address=ADDRESS The server ip or hostname, defaults to localhost")
        print("-w WINDOW_SIZE | --window=WINDOW_SIZE The window_size, defaults to 3")
        print("-h | --help Print this help")
    try:
        OPTS, ARGS = getopt.getopt(sys.argv[1:],
                                   "u:p:a:w", ["user=", "port=", "address=","window="])
    except getopt.error:
        helper()
        exit(1)

    PORT = 15000
    DEST = "localhost"
    USER_NAME = None
    WINDOW_SIZE = 3
    for o, a in OPTS:
        if o in ("-u", "--user="):
            USER_NAME = a
        elif o in ("-p", "--port="):
            PORT = int(a)
        elif o in ("-a", "--address="):
            DEST = a
        elif o in ("-w", "--window="):
            WINDOW_SIZE = a

    if USER_NAME is None:
        print("Missing Username.")
        helper()
        exit(1)

    S = Client(USER_NAME, DEST, PORT, WINDOW_SIZE)
    try:
        # Start receiving Messages
        T = Thread(target=S.receive_handler)
        T.daemon = True
        T.start()
        # Start Client
        S.start()
    except (KeyboardInterrupt, SystemExit):
        sys.exit()
