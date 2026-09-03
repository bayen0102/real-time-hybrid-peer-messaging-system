

#1.start tcp server
#2.wait for connection
#3.receive request
#4.process REGISTER or BRIDGE
#5.send response to client (use sendall)

import socket
import sys
import signal
import argparse
import select
from database import register_client, save_message
from redis_client import set_user_online
from logger import log_event

#---------------#
parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, required=True)
args = parser.parse_args()

port = args.port
host = socket.gethostbyname(socket.gethostname())

#server 必須 記錄所有 REGISTER 的 client
#key=clientID, value=(ip,port)
client_info = {} # stores registered clients

#1
srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)#AF_INET=ipv4, SOCK_STREAM=tcp
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)#allow port reuse
try:
    srv.bind(('', port))#把 server socket 綁定到指定 port
except socket.error as e:
    print(f"bind error: {e}", file=sys.stderr)
    sys.exit(1)
srv.listen(5) #讓 server 開始 等待 incoming connection5是 backlog queue size
log_event(
    "server_started",
    host=host,
    port=port
)


# handle ctrl c to close gracefully
def handler(sig, frame):
    srv.close()
    sys.exit(0)
signal.signal(signal.SIGINT, handler) #ctrlc->call handler()

#2.wait for connection
#main loop - wait for connections
while True:
    ready, _, _ = select.select([srv, sys.stdin], [], []) #srv=incoming client, stdin=terminal commmand

    for s in ready: #srv or stdin
        if s is srv: 
            #3.receive request
            conn, addr = srv.accept()
            data = conn.recv(4096).decode() #從 client 接收 message。
            if not data:
                conn.close()
                continue
            #4.process register/bridge
            #print(data) # debug
            lines = data.split('\r\n')
            req_type = lines[0].strip() #第一行永遠是regiser or bridge

            # parse headers into dict
            hdrs = {}
            for l in lines[1:]:
                if l == '':
                    break
                if ':' in l:
                    k, v = l.split(':', 1)
                    hdrs[k.strip()] = v.strip()

            if req_type == "REGISTER":
                cid = hdrs['clientID']
                cip = hdrs.get('IP', '')
                cport = hdrs.get('Port', '')
                register_client(cid, cip, cport) # save it to database
                set_user_online(cid) # set user online in redisclient_info[cid] = (cip, cport) # save it 把 client 存進 server database。

                client_info[cid] = (cip, cport) # save it 把 client 存進 server database。

                log_event(
                    "client_registered",
                    client_id=cid,
                    ip=cip,
                    port=int(cport)
                )
                                #5.send response(ues sendall)
                # send REGACK back
                resp = (f"REGACK\r\n"
                        f"clientID: {cid}\r\n"
                        f"IP: {cip}\r\n"
                        f"Port: {cport}\r\n"
                        f"Status: registered\r\n"
                        f"\r\n")
                conn.sendall(resp.encode())#把 response 傳回 client。

            elif req_type == "BRIDGE":
                who = hdrs.get('clientID', '') 

                # look for the other client thats not the one asking
                peer_name = ''
                peer_ip = ''
                peer_port = ''
                for c in client_info: #看是誰掃描所有 registered client。
                    if c != who: #find another client
                        peer_name = c
                        peer_ip = client_info[c][0]
                        peer_port = client_info[c][1]
                        break
                if who in client_info:
                    w_info = who + " " + client_info[who][0] + ":" + client_info[who][1]
                else:
                    w_info = who
                if peer_name:
                    log_event(
                        "peer_bridge_created",
                        client_id=who,
                        peer_id=peer_name,
                        peer_ip=peer_ip,
                        peer_port=int(peer_port)
                    )
                else:
                    log_event(
                        "peer_bridge_failed",
                        client_id=who
                    )

                # send back peer info
                resp = f"BRIDGEACK\r\n"
                resp += f"clientID: {peer_name}\r\n"
                resp += f"IP: {peer_ip}\r\n"
                resp += f"Port: {peer_port}\r\n"
                resp += "\r\n"
                conn.sendall(resp.encode())
            

            elif req_type == "LOG":
                sender = hdrs.get("sender", "")
                receiver = hdrs.get("receiver", "")
                message = hdrs.get("message", "")
                save_message(sender, receiver, message) # save it to database
                log_event(
                    "message_saved",
                    sender=sender,
                    receiver=receiver,
                    message_length=len(message)
                )
            else:
                # not a valid request type :not register or bridge
                print("Malformed incoming message", file=sys.stderr)
                conn.close()
                srv.close()
                sys.exit(1)

            conn.close()

        elif s is sys.stdin:# terminal command
            cmd = sys.stdin.readline().strip()
            if cmd == "/info":
                for c in client_info:
                    print(c + " " + client_info[c][0] + ":" + client_info[c][1])