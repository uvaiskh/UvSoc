import socket
import threading
from multiprocessing.pool import ThreadPool
from functools import partial
import json
import logging
from datetime import datetime, timedelta
import uuid
from config import HOST, PORT

logging.basicConfig(level=logging.INFO)

LISTNER_LIMIT = 10

FEED_CLIENT = []


RECIEVE_CLIENTS = {}
RECIEVE_CLIENTS_EXPIRY = {}
TOKEN_CLIENTS = {}

def listen_for_meassages(client):
    while True:
        message = client.recv(2048).decode('utf-8')
        if message:
            try:
                message = json.loads(message)
                send_messasge_to_all(message)
            except Exception as e:
                print(e)
                pass


def listen_receiver_client(client):
    while True:
        message = client.recv(2048).decode('utf-8')
        message = json.loads(message)


def client_handler(client):
    is_feeder = False
    msg = json.dumps({"status": False, "type": "connection"})
    while True:
        connection_msg = client.recv(2048).decode('utf-8')
        try:
            connection_msg = json.loads(connection_msg)
            user_type = connection_msg.get('user_type')
            token = connection_msg.get('token')
            if user_type == 'feeder':
                FEED_CLIENT.append(client)
                msg = json.dumps({"status": True, "type": "connection", "data":{"client_type": "feeder"}})
                is_feeder = True
                break
            elif user_type == 'receiver':
                id = str(uuid.uuid4())
                RECIEVE_CLIENTS[id] = client
                RECIEVE_CLIENTS_EXPIRY[id] = datetime.now() + timedelta(minutes=1)
                if token not in TOKEN_CLIENTS:
                    TOKEN_CLIENTS[token] = list()
                TOKEN_CLIENTS[token].append(id)
                threading.Thread(target=check_for_expiry, args=(id,)).start()
                msg = json.dumps({"status": True, "type": "connection", "data":{"client_type": "receiver"}})
                print(TOKEN_CLIENTS)
                break
            else:
                break
        except:
            break
    
    client.sendall(msg.encode())
    if is_feeder:
        threading.Thread(target=listen_for_meassages, args=(client,)).start()

def send_message_to_a_reciver(message, client_id):
    RECIEVE_CLIENTS[client_id].sendall(message.encode())

def send_messasge_to_all(message):
    token = message.get('token')
    clients_ids = TOKEN_CLIENTS.get(token)
    message = json.dumps(message)
    if clients_ids:
        pool = ThreadPool(len(clients_ids))
        func = partial(send_message_to_a_reciver, message)
        pool.map(func, clients_ids)
        pool.close()
        pool.join()


def check_for_poll(id):
    client = RECIEVE_CLIENTS[id]
    client.settimeout(60)
    while True:
        try:
            message = client.recv(2048).decode('utf-8')
            if message == 'poll':
                RECIEVE_CLIENTS_EXPIRY[id] = datetime.now() + timedelta(minutes=1)
        except:
            break
    

def check_for_expiry(id):
    threading.Thread(target=check_for_poll, args=(id,)).start()
    while True:
        if RECIEVE_CLIENTS_EXPIRY[id] < datetime.now():
            break
    logging.info(f"Removed client, ID: {id}")
    del RECIEVE_CLIENTS[id]
    del RECIEVE_CLIENTS_EXPIRY[id]
    token = None
    for tkn, client_ids in TOKEN_CLIENTS.items():
        if id in client_ids:
            token = tkn
            break
    if token:
        if len(TOKEN_CLIENTS[token]) <= 1:
            TOKEN_CLIENTS.pop(token)
        else:
            TOKEN_CLIENTS[token].remove(id)
    
    print(TOKEN_CLIENTS)
            

        
def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind((HOST, PORT))
        logging.info(f"Server starts running, HOST {HOST}, PORT: {PORT}, ")
    except Exception as e:
        logging.error(f"Server failed to start: ERROR: {e}")
    
    server.listen(LISTNER_LIMIT)

    while True:
        try:
            client, address = server.accept()
            threading.Thread(target=client_handler, args=(client,)).start()
            logging.info("client connected..")
        except:
            pass

if __name__ == '__main__':
    main()
