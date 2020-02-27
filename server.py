'''
This module defines the behaviour of server in your Chat Application
'''
import sys
import getopt
import socket
import util
import time
import random
import queue
from threading import Thread


class Server:
    '''
    This is the main Server Class. You will to write Server code inside this class.
    '''
    def __init__(self, dest, port, window):
        self.server_addr = dest
        self.server_port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(None)
        self.sock.bind((self.server_addr, self.server_port))
        self.window = window
        self.clients = {}
        self.packet_buff = {}
        self.packet_history = {}
        self.ack_buffer = {}
        self.ack_queue = {}
        self.packet_num = -1


    def send_res(self,res,addr):
        self.sock.sendto(res.encode("utf-8"),addr)
        print("sent:",res)

    def send_ack(self,packet,addr):
        
        packets = self.packet_buff[addr]

        packets = sorted(packets.keys())
       

        for n in packets:
            if str(int(n)+1) not in packets:
                ack = util.make_packet("ack",int(n)+1,"")
                self.send_res(ack,addr)
                break

    def getPacketsFromBuffer(self,addr):
        packets = []

        for u in self.packet_buff[addr]:
            packets.append(self.packet_buff[addr][u])

        return packets

    def resetBuffer(self,addr):
        self.packet_buff.pop(addr)        
        

    def incrementPacketn(self,packn):
        packn = packn+1
        return packn

    def waitAndreSend(self,packet,addr):
        msg_type,seqno,message,checksum = util.parse_packet(packet)

        pack_n = int(seqno) + 1
        t_time = 0
        while int(self.ack_buffer[addr]) != pack_n:
            #print("ack recv",self.ack_buffer[addr])
            #print("self pack n",pack_n)
            time.sleep(0.1)
            t_time=t_time+1
            if t_time == 5:
                if int(self.ack_buffer[addr]) != pack_n:
                    t_time = 0
                    print("resending")
                    self.send_res(packet,addr)
        
                        

    def startWaitAndResend(self,packet,addr):
        self.waitAndreSend(packet,addr)

    def reset_ack_queue(self,addr):
        q = self.ack_queue[addr]
        while not q.empty():
            q.get()


    def start_conn(self,addr,packNum):
        start = util.make_packet("start",packNum,"")
        self.send_res(start,addr)
        self.startWaitAndResend(start,addr)
        self.reset_ack_queue(addr)

    def end_conn(self,addr,packNum):
        end = util.make_packet("end",packNum,"")
        self.send_res(end,addr)
        self.startWaitAndResend(end,addr)
        self.reset_ack_queue(addr)

    def send_tcp(self,packet,addr,packNum):
        packNum = self.incrementPacketn(packNum)
        self.start_conn(addr,packNum)
        packNum = self.incrementPacketn(packNum)
        res_packet = util.make_packet("data",packNum,packet)
        self.send_res(res_packet,addr)
        self.waitAndreSend(res_packet,addr)
        packNum = self.incrementPacketn(packNum)
        self.end_conn(addr,packNum)
                        
    def send_window_tcp(self,chunks,addr,packNum):
        packNum = self.incrementPacketn(packNum)
        self.start_conn(addr,packNum)
        '''
        send using window. to be implemented    
        
        '''
        b = 0
        w = self.window
        sent = False
        seqno = packNum + 1
        packet_history = []    
        packets = [] 
        for ps in chunks:
            packets.append(ps)


        for i in range(0,len(chunks)):
            packNum  = self.incrementPacketn(packNum)
            packets[i] = util.make_packet("data",packNum,packets[i])   

        to_send = 0
        t_time = 0
        while b < len(chunks):
            while to_send < b + w and to_send < len(chunks):
                
                packet = packets[to_send]
                packet_history.append(packet)
                self.send_res(packet,addr)
                to_send = to_send + 1
            #while (True):
            #time.sleep(2)
           # try:
                #num_of_pckt_rcvd = self.ack_buffer - seqno
            ack_q = self.ack_queue[addr]
            tmp = ack_q.get(timeout=0.5)
            print("ack---------->>>>>>",tmp)
            num_of_pckt_rcvd = int(tmp) - seqno
            print("n recvd",num_of_pckt_rcvd)
            #time.sleep(5)
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
            #except:
                #t_time = 0
           #     to_send = b
                #break  
        packNum = self.incrementPacketn(packNum)

        self.end_conn(addr,packNum)                  

    def extract_message(self,msg,addr):
        total_recievers = msg[2]
        total_recievers = int(total_recievers)
        recievers = []
        sender = ''
        for s in self.clients:
            if self.clients[s] == addr:
                sender = s
        sender = str(sender)
        for i in range(3,total_recievers+3):
            recievers.append(msg[i])
        text = ''
        for i in range(total_recievers+3,len(msg)):
            text = text + " " + msg[i]
        text = text.strip()
        tmp = "1 " + sender + " " + text
        res = util.make_message("forward_message",4,tmp)
        recievers = list(dict.fromkeys(recievers))
        return res,recievers,sender

    def processAndServe(self,addr):
        MAX_NUM_CLIENTS = 10
        ERR_SERVER_FULL = "err_server_full 0"
        ERR_USERNAME_UNAVAILABLE = "err_username_unavailable 0"
        ERR_UNKNOWN_MESSAGE = "err_unknown_message 0"
        packet_number = random.randint(0, 40000)
        all_packets = self.getPacketsFromBuffer(addr)
        print("packets",all_packets)
        msg_type,seqno,message,checksum = util.parse_packet(all_packets[1])

        if msg_type == "data":
            msg_unsplit = message
            msg = message.split()
            msg_cmd = msg[0]
            res = ''
           
            if msg_cmd == "join":
                if len(self.clients) < MAX_NUM_CLIENTS:
                    duplicate_flag = False
                    for user in self.clients:
                        if user == msg[2]:
                            duplicate_flag = True

                    if duplicate_flag:
                        res = ERR_USERNAME_UNAVAILABLE
                        self.send_tcp(res,addr,packet_number)
                        print("disconnected: username unavailable")
                    if not duplicate_flag:
                        self.clients[msg[2]] = addr
                        print("join:",msg[2])
                else:
                    res = ERR_SERVER_FULL
                    self.send_tcp(res,addr,packet_number)
                    print("disconnected: server full")

            elif msg_cmd == "request_users_list":
                total_clients = len(self.clients)
                all_clients = ""
                for u in sorted(self.clients.keys()):
                    all_clients = all_clients + u + " "
                all_clients = all_clients.strip()
                tmp = str(total_clients) + " " + all_clients                
                for s in self.clients:
                    if self.clients[s] == addr:
                        res = util.make_message("response_users_list",3,tmp)
                        self.send_tcp(res,addr,packet_number)
                        sender = s
                print("request_users_list:",sender)
            
            elif msg_cmd == "disconnect":
                client_to_disconnect = msg[2]
                self.clients.pop(client_to_disconnect)
                print("disconnected:",client_to_disconnect)
            
            elif msg_cmd == "send_message":
                # total_recievers = msg[2]
                # total_recievers = int(total_recievers)
                # recievers = []
                # sender = ''
                # for s in self.clients:
                #     if self.clients[s] == addr:
                #         sender = s
                # sender = str(sender)
                # for i in range(3,total_recievers+3):
                #     recievers.append(msg[i])
                # text = ''
                # for i in range(total_recievers+3,len(msg)):
                #     text = text + " " + msg[i]
                # text = text.strip()
                # tmp = "1 " + sender + " " + text
                # res = util.make_message("forward_message",4,tmp)
                # recievers = list(dict.fromkeys(recievers))
                res,recievers,sender = self.extract_message(msg,addr)
                chunks = []
                chunks.append(res)
                if len(res) <= 1400:

                    for r in recievers:
                        if not r in self.clients:
                            print("msg:",sender,"to non-existent user",r)
                        else:
                            # res_packet = util.make_packet("data",0,res)
                            # self.send_res(res_packet,self.clients[r])
                            #self.send_tcp(res,self.clients[r],packet_number)
                            self.send_window_tcp(chunks,self.clients[r],packet_number)
                            packet_number = packet_number + len(chunks) + 2

                else:
                    numberOfPackets = int(len(req)/1400)+1
                    size = 1400
                    for i in range(0,numberOfPackets):
                        chunks.append(req[i*size:(i+1)*size])
                    tmp_str = ""                 
                    tmp_str = chunks[0]
                    tmp_str = tmp_str[21:]
                    chunks[0] = util.make_message("forward_message",4,tmp_str)
                    print("msg:",sender)
                    for r in recievers:
                        if not r in self.clients:
                            print("msg:",sender,"to non-existent user",r)
                        else:
                            # res_packet = util.make_packet("data",0,res)
                            # self.send_res(res_packet,self.clients[r])
                            self.send_window_tcp(chunks,self.clients[r],packet_number)
            
            elif msg_cmd == "send_file":
                total_recievers = msg[2]
                total_recievers = int(total_recievers)
                recievers = []
                sender = ''
                for s in self.clients:
                    if self.clients[s] == addr:
                        sender = s
                sender = str(sender)

                for i in range(3,total_recievers+3):
                    recievers.append(msg[i])
                file_name = msg[total_recievers+3]
                d = msg_unsplit.split("<delimtter>")

                text = d[1]
                tmp = "1 " + sender + " " + file_name + " <delimtter>" + text
                res = util.make_message("forward_file",4,tmp)
                print("file:",sender)
                recievers = list(dict.fromkeys(recievers))
                for r in recievers:
                    if not r in self.clients:
                        print("file:",sender,"to non-existent user",r)
                    else:
                        #res_packet = util.make_packet("data",0,res)
                        self.send_tcp(res,self.clients[r],packet_number)
            
            else:
                res_packet = util.make_packet("data",0,ERR_UNKNOWN_MESSAGE)
                self.send_res(res_packet,addr)
                for s in self.clients:
                    if self.clients[s] == addr:
                        print("disconnected:",s,"sent unknown command")
                        self.clients.pop(s)
            self.resetBuffer(addr)
            sys.exit()
        



                    


    def start(self):
        '''
        Main loop.
        continue receiving messages from Clients and processing it
        '''
        while True:
            start = False
            end = False

            #wait and recieve all the data && buffer them
            while(start == False or end == False):
                packet,addr  = self.sock.recvfrom(4096)
                if addr not in self.ack_buffer or addr not in self.ack_queue:
                    self.ack_buffer[addr] = -1
                    self.ack_queue[addr] = queue.Queue()

                print("recieved:",packet.decode("utf-8"))
                p_type,seqno,message,checksum = util.parse_packet(packet.decode("utf-8"))
                if p_type == "ack":
                    self.ack_buffer[addr] = seqno
                    q = self.ack_queue[addr]
                    q.put(seqno)
                    

                #create a buffer for the incoming address
                if addr not in self.packet_buff:
                    self.packet_buff[addr] = {}
                
                #store the packets in the buffer
                if p_type != "ack":
                    self.packet_buff[addr][seqno] = packet.decode("utf-8")
               
                #checks whether complete packets were recieved or not               
                if p_type == "start":
                    start = True
                if p_type == "end":
                    end = True
                #dont send acknowledgment for acknowledgment
                tmp = message.split()

                if p_type != "ack":
                    self.send_ack(packet,addr)


            print("new thread")
            
            processDataThread = Thread(target=self.processAndServe,args=(addr,))
            processDataThread.daemon = True
            processDataThread.start()
            
            
                
            
                

           







# Do not change this part of code

if __name__ == "__main__":
    def helper():
        '''
        This function is just for the sake of our module completion
        '''
        print("Server")
        print("-p PORT | --port=PORT The server port, defaults to 15000")
        print("-a ADDRESS | --address=ADDRESS The server ip or hostname, defaults to localhost")
        print("-w WINDOW | --window=WINDOW The window size, default is 3")
        print("-h | --help Print this help")

    try:
        OPTS, ARGS = getopt.getopt(sys.argv[1:],
                                   "p:a:w", ["port=", "address=","window="])
    except getopt.GetoptError:
        helper()
        exit()

    PORT = 15000
    DEST = "localhost"
    WINDOW = 3

    for o, a in OPTS:
        if o in ("-p", "--port="):
            PORT = int(a)
        elif o in ("-a", "--address="):
            DEST = a
        elif o in ("-w", "--window="):
            WINDOW = a

    SERVER = Server(DEST, PORT,WINDOW)
    try:
        SERVER.start()
    except (KeyboardInterrupt, SystemExit):
        exit()
