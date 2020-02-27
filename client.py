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
        self.ack_queue = queue.Queue()
        
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

    def reset_ack_queue(self):
        while not self.ack_queue.empty():
            self.ack_queue.get()

    def start_conn(self):
        self.incrementPacketn()
        start = util.make_packet("start",self.packet_num,"")
        self.send_req(start)
        self.waitAndreSend(start)
        self.ack_queue.queue.clear
        self.reset_ack_queue()
    
    def end_conn(self):
        self.incrementPacketn()
        end = util.make_packet("end",self.packet_num,"")
        self.send_req(end)
        self.waitAndreSend(end)
        self.reset_ack_queue()


    def send_tcp(self,req):
        self.start_conn()
        self.incrementPacketn()
        packet = util.make_packet("data",self.packet_num,req)
        self.send_req(packet)
        self.waitAndreSend(packet)
        self.end_conn()


    def send_window_tcp(self,chunks):
        self.start_conn()
        '''
        send using window. to be implemented    
        
        '''
        b = 0
        w = self.window
        sent = False
        seqno = self.packet_num + 1
        packet_history = []     

        for i in range(0,len(chunks)):
            self.incrementPacketn()
            chunks[i] = util.make_packet("data",self.packet_num,chunks[i])   

        to_send = 0
        t_time = 0
        while b < len(chunks):
            while to_send < b + w and to_send < len(chunks):
                
                packet = chunks[to_send]
                packet_history.append(packet)
                self.send_req(packet)
                to_send = to_send + 1
            #while (True):
            #time.sleep(2)
            try:
                #num_of_pckt_rcvd = self.ack_buffer - seqno
                tmp = self.ack_queue.get(timeout=5)
                print("ack---------->>>>>>",tmp)
                num_of_pckt_rcvd = tmp - seqno
                #ack = self.ack_queue.get(timeout=0.5)
                if (num_of_pckt_rcvd > 0):
                    print("sliding window forward by",num_of_pckt_rcvd)
                    
                    b = b + num_of_pckt_rcvd
                    seqno = seqno + num_of_pckt_rcvd 
                    
                #else:
                    #to_send = b
                    #break
                # time.sleep(0.1)
                # t_time=t_time+1
                #if t_time == 5:
            except:
                #t_time = 0
                to_send = b
                #break            





        # while to_send < b + w and b<len(chunks):
            
        #     self.incrementPacketn()
        #     packet = util.make_packet("data",self.packet_num,chunks[to_send])
        #     packet_history.append(packet)
        #     self.send_req(packet)
        #     to_send = to_send + 1
        #     if(to_send % w ==0 or to_send == len(chunks)):
        #         t_time = 0
        #         while (True):
        #             num_of_pckt_rcvd = self.ack_buffer - seqno
        #             if (num_of_pckt_rcvd > 0) and not(to_send >= len(chunks)):
        #                 print("sliding window forward")
        #                 b = b + num_of_pckt_rcvd
        #                 seqno = seqno + num_of_pckt_rcvd 
        #                 break
        #             time.sleep(0.1)
        #             t_time=t_time+1
        #             if t_time == 5:
        #                 t_time = 0
        #                 to_send = b
        #                 break
                            
                    

            
            

            




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
        

    def extract_message(self,cmd):
        to_clients = ""
        no_clients = cmd[1]
        no_clients = int(no_clients)
        print(cmd)
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
            print("input",cmd)
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
            
               # try:
                   

                    tmp = self.extract_message(cmd)
                    req = util.make_message("send_message",4,tmp)
                    print("message:",tmp)
                    print("length:",len(req))
                    # stri = "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"
                    # print("actual length",len(stri))

                    if len(req) <= 1400:
                        self.send_tcp(req)
                    else:
                        numberOfPackets = int(len(req)/1400)+1
                        chunks = []
                        size = 1400
                        for i in range(0,numberOfPackets):
                            chunks.append(req[i*size:(i+1)*size])
                        tmp_str = ""                 
                        tmp_str = chunks[0]
                        tmp_str = tmp_str[18:]
                        chunks[0] = util.make_message("send_message",4,tmp_str)
                        self.send_window_tcp(chunks)

 
            #   #  except:
            #         print("arguments to \"msg\" are incomplete")
            #         print("enter \"help\"")
                    
                
            elif cmd_type == "file":
                #try:
                tmp = self.extract_file(cmd)
                req = util.make_message("send_file",4,tmp)
                print("length:",len(req))

                if len(req) <= 1400:
                    self.send_tcp(req)
                else:
                    numberOfPackets = int(len(req)/1400)+1
                    chunks = []
                    size = 1400
                    for i in range(0,numberOfPackets):
                        chunks.append(req[i*size:(i+1)*size])
                    tmp_str = ""                 
                    tmp_str = chunks[0]
                    tmp_str = tmp_str[15:]
                    chunks[0] = util.make_message("send_file",4,tmp_str)
                    self.send_window_tcp(chunks)
                #except:
                    # print("arguments to \"file\" incomplete")
                    # print("enter \"help\"")



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
                    self.ack_queue.put(int(seqno))
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
