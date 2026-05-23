
#1.init client 
#2.parse arguments
#3.create listening socket(for chat peer-peer connection)
#4.INIT state
#5./register
#6./bridge
#7.if peer empty-> WAIT
#. if peer exists -> /chat
#8.WAIT state
#9. peer-to-peer tcp connection(connect() or accept())
#10. CHAT mode
#11. do_chat()
#12.exchange chat messages using persistent tcp
#13 /quit

import socket
import argparse
import select
import sys
import signal

#2.
#when run: python3 p2-lhuang77-baewang-client.py --id alice --port 3000 --server..
#為了讀取啟動client的參數，使用argparse模組來解析命令行參數。這些參數包括client的ID、port以及server的地址和端口。
parser = argparse.ArgumentParser()
parser.add_argument("--id", required=True)
parser.add_argument("--port", type=int, required=True)
parser.add_argument("--server", required=True)
args = parser.parse_args()

client_id = args.id
client_port = args.port
server_ip, server_port = args.server.split(":")
server_port = int(server_port)

peer_id = None
peer_ip = None
peer_port = None

state = "INIT" #INIT(/id, /register, /bridge, /chat, /quit)->wait(/id, /quit)->chat(/quit)
listen_sock = None #在wait state用 等待peer connection
chat_sock = None #在do_chat() peer<->peer chat:persistent tcp代表只開一個連接
local_ip = "127.0.0.1"
#-----------------------------------------------------------------------------------------------
#1connect to server(startup message)
print(f"{client_id} running on 127.0.0.1:{client_port}")

#helper:shutdown and close sockets: /quit or ctrlc
def close_all():
    global chat_sock, listen_sock
    for s in (chat_sock, listen_sock):
        if s:
            try:
                s.close()
            except Exception:
                pass
    chat_sock = listen_sock = None

#helper: signal handler(ctrlc)為了能安全capture CTRL-C 安全關閉！！project requirment: “program must close gracefully”
def signal_handler(sig, frame):
    close_all()
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

#3.create listen socket
#listen socket:只監聽incoming TCP connection
#bind+listen 準備接收連接 真正連接是到wait state才accept
def setup_listen_socket():
    global listen_sock
    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)#ipv4, tcp
    listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        listen_sock.bind(("", client_port)) #this program usage this port to listen for peer connection, so bind to client_port
        listen_sock.listen(1) #allow another peer to connect
    except socket.error as e:
        raise SystemExit(f"Socket error binding listen socket: {e}") from e
setup_listen_socket()

#這很重要這裡是client <-> server 代表是non-persistent
#每次都是發送 register, bridge!
#send 1 request to server:/register and /bridge
#connect server(tcp)->send request->read response->close socket
def send_to_server(msg: str):
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #create tcp socket
        s.connect((server_ip, server_port)) #tcp 3-way
        s.sendall(msg.encode()) #send register or bridge request 不生成message只負責“發送“
        s.shutdown(socket.SHUT_WR) #signal end of request
        s.settimeout(5) #防止server不回應否则 recv()会无限等待
        buf = b""
        try:
            while b"\r\n\r\n" not in buf and b"\n\n" not in buf:
                chunk = s.recv(4096) #這部分是為读取 server response
                if not chunk:
                    break
                buf += chunk #因爲response可能分多次到达，所以需要循环读取直到完整的响应被接收（以\r\n\r\n或\n\n结尾）。
        except socket.timeout:
            pass
        return buf.decode()
    except socket.error as e:   
        raise ValueError(f"Socket error communicating with server: {e}") from e
    finally:#不管成功与否都要关闭socket 這也是non-persistent的特點close after each request
        if s:
            s.close()

#. 這裡是為了能讓
#. REGACK
#  clientID: Alice
#  IP: 127.0.0.1
#. Port: 3000
#可以轉成-> 
# msg_type
# headers dictionary 
# 方便program read 
# headers["IP"]
# headers["Port"]

#parse response/request into
def parse_message(raw: str):
    headers = {}
    lines = raw.split("\r\n")
    msg_type = lines[0].strip()
    for line in lines[1:]:
        if ":" in line:
            key, val = line.split(":", 1)
            headers[key.strip()] = val.strip()
    return msg_type, headers

#11 state==chat 這裡是peer<->peer chat : persistent tcp代表只開一個連接
#這裡是為了能讓peer之間可以互相聊天，使用select來同時監聽標準輸入和socket，實現非阻塞的聊天功能。
#目標：同时监听：用戶輸入和peer消息
# Bob(initiator) write first, Alice(acceptor) read first
#if i_am_writer=true(bob/initiator) write
#if i_am_writer=false(alice/acceptor) read 
#write ->read->write->read
#sock=peer發來, sys.stdin=用戶輸入
def do_chat(sock: socket.socket, i_am_writer: bool):
    writing = i_am_writer
    while True: 
        if writing:#當前client is writer
            readable, _, _ = select.select([sys.stdin, sock], [], []) #monitor stdin and socket
            if sock in readable: #peer發來message or QUIT:假設是alice突然傳訊或quit
                data = sock.recv(4096)
                if not data:
                    break
                msg = data.decode()
                if msg.startswith("QUIT"):
                    break
                print(msg.rstrip("\r\n")) #print peer message
            if sys.stdin in readable: #用戶輸入message or /quit:假設是bob
                line = sys.stdin.readline()
                if not line:
                    break
                line = line.rstrip("\n")
                #13/quit
                if line == "/quit":
                    try:
                        sock.sendall("QUIT\r\n\r\n".encode())
                    except socket.error:
                        pass
                    sock.close()
                    break
                try:
                    sock.sendall((line + "\r\n").encode())
                except socket.error as e:
                    print(f"Socket error sending message: {e}", file=sys.stderr)
                    break
                log_msg = (f"LOG\r\n"
                    f"sender: {client_id}\r\n"
                    f"receiver: {peer_id}\r\n"
                    f"message: {line}\r\n"
                    f"\r\n")
                try:
                    send_to_server(log_msg)
                except Exception as e:
                    print(f"LOG error: {e}", file=sys.stderr) 
                writing = False #switch role: writer → reader
        else: #當前client is reader
            readable, _, _ = select.select([sock, sys.stdin], [], [])
            if sys.stdin in readable: #alice can quit the terminal if bob chat first.
                line = sys.stdin.readline().rstrip("\n")
                if line == "/quit":
                    try:
                        sock.sendall("QUIT\r\n\r\n".encode())
                    except socket.error:
                        pass
                    break
            if sock in readable: #peer sent message如果bob先傳訊息，alice就會在這裡收到
                try:
                    data = sock.recv(4096)
                except socket.error as e:
                    print(f"Socket error receiving message: {e}", file=sys.stderr)
                    break #since break here do not change to raise valueerror.
                if not data:
                    break
                msg = data.decode()
                if msg.startswith("QUIT"):
                    break
                print(msg.rstrip("\r\n")) #print peer message
                writing = True #switch role: reader → writer 對方寫完換我寫
    try:
        sock.close()
    except Exception:
        pass

#4-------------main--------------
try:
    while True:
        #8 wait state
        if state == "WAIT": #use select to monitor both listen_sock and sys.stdin, so that we can accept peer connection and also allow user to input /id or /quit while waiting for peer connection.
            readable, _, _ = select.select([listen_sock, sys.stdin], [], [])
            if listen_sock in readable:
                conn, addr = listen_sock.accept() #9 peer connect to my listen socket, accept connection
                chat_sock = conn
                buf = b""
                while b"\r\n\r\n" not in buf:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    buf += chunk
                msg_type, headers = parse_message(buf.decode())
                incoming_peer_id = headers.get("clientID", addr[0])
                print(f"Incoming chat request from {incoming_peer_id} "
                      f"{addr[0]}:{addr[1]}")
                 #10 alice read first
                do_chat(conn, i_am_writer=False) 
                close_all()
                sys.exit(0)
            if sys.stdin in readable:
                cmd = sys.stdin.readline().strip()
                if cmd == "/id":
                    print(client_id)
                elif cmd == "/quit":
                    close_all()
                    sys.exit(0)
        ##4init state
        else: 
            cmd = input().strip()
            if cmd == "/id":
                print(client_id)
            #5.send request to server(register/bridge) 
            elif cmd == "/register":
                msg = (f"REGISTER\r\n"
                       f"clientID: {client_id}\r\n"
                       f"IP: {local_ip}\r\n"
                       f"Port: {client_port}\r\n"
                       f"\r\n") #msg: client -> server

                try:
                    response = send_to_server(msg) #sent to server
                    print(response.strip())
                    resp_type, headers = parse_message(response)#parse response
                except ValueError as e:
                    print(e, file=sys.stderr)
            #6. bridge
            elif cmd == "/bridge":
                msg=(f"BRIDGE\r\n"
                     f"clientID: {client_id}\r\n"
                     f"\r\n")
                
                try:
                    response = send_to_server(msg) #send to server
                    print(response.strip())
                    resp_type, headers = parse_message(response)
                    #7: if peer is empty
                    if resp_type == "BRIDGEACK":
                        peer_id = headers.get("clientID", "")
                        peer_ip = headers.get("IP", "")
                        peer_port_str = headers.get("Port", "")
                        if peer_id and peer_ip and peer_port_str: #means 三個都不為空＝peer exist
                            peer_port = int(peer_port_str) #client2(bob) has peer info
                        else: #7 if peer empty->WAIT client1(alice): empty bridgeack->wait
                            state = "WAIT"
                except ValueError as e:
                    print(e, file=sys.stderr)

            elif cmd == "/chat":
            #only client2(bob) can run /chat
                if peer_ip and peer_port:
                    try:
                        #chat_sock 建立在這！！為了能夠peer to peer chat
                        chat_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        chat_sock.connect((peer_ip, peer_port))
                        chat_msg = (f"CHAT\r\n"
                                     f"clientID: {client_id}\r\n"
                                     f"\r\n")
                        chat_sock.sendall(chat_msg.encode())
                        do_chat(chat_sock, i_am_writer=True) #bob write first
                    except socket.error as e:
                        print(f"Socket error initiating chat: {e}", file=sys.stderr)
                    close_all()
                    sys.exit(0)
                else:
                    print("No peer information available (run bridge)")
            elif cmd == "/quit": 
                close_all()
                sys.exit(0)
except KeyboardInterrupt:
    close_all()