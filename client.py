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
        self.packet_queue = queue.Queue()
        self.packet_buff = {}
        self.packet_history = {}
        self.ack_buffer = -1
        
        self.packet_num = -1
        self.window = window_size

    def send_ack(self,packet):
        
        packets = self.packet_buff

        packets = sorted(packets.keys())
       

        for n in packets:
            if str(int(n)+1) not in packets:
                ack = util.make_packet("ack",int(n)+1,"")
                self.send_req(ack)
                break

    def getPacketsFromBuffer(self):
        packets = []

        for u in self.packet_buff:
            packets.append(self.packet_buff[u])

        return packets

    def resetBuffer(self):
        self.packet_buff = {}     
    
    def incrementPacketn(self):
        self.packet_num = self.packet_num+1

    def waitAndreSend(self,packet):
        pack_n = int(self.packet_num) + 1
        t_time = 0
        while self.ack_buffer != pack_n:
            time.sleep(0.1)
            t_time=t_time+1
            if t_time == 5:
                if self.ack_buffer!=pack_n:
                    t_time = 0
                    self.send_req(packet)


    def start_conn(self):
        self.incrementPacketn()
        start = util.make_packet("start",self.packet_num,"")
        self.send_req(start)
        self.waitAndreSend(start)
    
    def end_conn(self):
        self.incrementPacketn()
        end = util.make_packet("end",self.packet_num,"")
        self.send_req(end)
        self.waitAndreSend(end)

    def send_tcp(self,req):
        self.start_conn()
        self.incrementPacketn()
        packet = util.make_packet("data",self.packet_num,req)
        self.send_req(packet)
        self.waitAndreSend(packet)
        self.end_conn()

    def join(self):
        req = ""
        self.start_conn()

        join_req = util.make_message("join",1,self.name)
        self.incrementPacketn()
        packet = util.make_packet('data',self.packet_num,join_req)
        self.send_req(packet)  
        self.waitAndreSend(packet)

        self.end_conn()
        

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
            #time.sleep(2)
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
                    
                    req = util.make_message("send_message",4,tmp)
                    packet = util.make_packet("data",0,req)
                    self.send_req(packet)
                except:
                    print("arguments to \"msg\" are incomplete")
                    print("enter \"help\"")
                    
                
            elif cmd_type == "file":
                try:

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

                        req = util.make_message("send_file",4,tmp)
                        packet = util.make_packet("data",0,req)
                    
                        f.close()
                        self.send_req(packet)
                    except:
                        print("file not found")
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
        print("sent:",req)
        self.sock.sendto(req.encode("utf-8"),(self.server_addr,self.server_port))



    def receive_handler(self):
        '''
        Waits for a message from server and process it accordingly
        '''
       
        while True:
            start = False
            end = False
            while(start == False or end == False):
                packet = self.sock.recv(4096)
                print("recieved:",packet.decode("utf-8"))
                p_type,seqno,res,checksum = util.parse_packet(packet.decode("utf-8"))
                if(p_type=="ack"):
                    self.ack_buffer = int(seqno)
                    print(self.ack_buffer)
                if p_type != "ack":
                    self.packet_buff[seqno] = packet.decode("utf-8")
                if p_type == "start":
                    start = True
                if p_type == "end":
                    end = True
                if p_type!="ack":
                    self.send_ack(packet)
            
            print(self.packet_buff)
            
            all_packets = self.getPacketsFromBuffer()

            print("packets",all_packets)
           
           
            p_type,seqno,res,checksum = util.parse_packet(all_packets[1])

            if p_type == "data":

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
                    # format: forward_message 22 1 client1 hello again!
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
                # print("disconnected: server received an unknown command")
                    os._exit(1)
            
            elif p_type == "ack":
                self.ack_buffer = int(seqno)
                print(self.ack_buffer)
            self.resetBuffer()




               






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
