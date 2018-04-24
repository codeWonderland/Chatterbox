#!/usr/bin/env python3
# Foundations of Python Network Programming, Third Edition
# https://github.com/brandon-rhodes/fopnp/blob/m/py3/chapter07/srv_asyncio2.py
# Asynchronous I/O inside an "asyncio" coroutine.

# Last modified by Alice Easter && Eric Cacciavillani on 4/6/18
import json

import argparse
import asyncio
import ssl
import struct
import pickle


class AsyncServer(asyncio.Protocol):
    transport_map = {}
    messages = []
    all_users_ever_logged = set()
    client_blocked_users = dict()

    def __init__(self):
        super().__init__()
        self.username = ""
        self.thread_transport = None
        self.current_transport = None
        self.__buffer = ""
        self.data_len = 0
        
        with open('server_data.pkl', 'rb') as f:
            AsyncServer.messages = pickle.load(f)
            AsyncServer.all_users_ever_logged = pickle.load(f)
            AsyncServer.client_blocked_users = pickle.load(f)
    def __del__(self):

        with open('server_data.pkl', 'wb') as f:
            pickle.dump(AsyncServer.messages, f)
            pickle.dump(AsyncServer.all_users_ever_logged, f)
            pickle.dump(AsyncServer.client_blocked_users, f)
        

    def connection_made(self, transport):
        self.thread_transport = transport
        self.current_transport = transport

    def send_message(self, data):
        msg = b''
        msg += struct.pack("!I", len(data))
        msg += data
        self.current_transport.write(msg)

    def broadcast(self, audience, data):
        if audience is self.username:
            self.current_transport = self.thread_transport
            self.send_message(data)
        elif audience == 'ALL':
            for user in AsyncServer.transport_map:
                
                if not ((user in AsyncServer.client_blocked_users) and self.username in AsyncServer.client_blocked_users[user]):
                    self.current_transport = AsyncServer.transport_map[user]
                    self.send_message(data)
                    
        # HERE TOO
        elif audience in AsyncServer.transport_map:
            
            self.current_transport = AsyncServer.transport_map[audience]
            self.send_message(data)
        else:
            self.current_transport = self.thread_transport
            msg = {"ERROR": "Specified username does not exist (or at least is not online)"}
            msg = json.dumps(msg).encode('ascii')
            self.send_message(msg)

    def data_received(self, data):
        if self.__buffer == '':
            # Find first brace and offset the data by that
            brace_index = data.find(b'{')
            self.data_len = struct.unpack("!I", data[0:brace_index])[0]
            data = data[brace_index:(self.data_len + brace_index)]

        data = data.decode('ascii')

        self.__buffer += data

        if len(self.__buffer) == self.data_len:
            data = json.loads(self.__buffer)
            self.__buffer = ""
            self.data_len = 0

            for key in data:
                if key == "USERNAME":
                    self.make_user(data)

                elif key == "MESSAGES":
                    print("Testing")
                    self.handle_messages(data)

                else:
                    print("New message type!!! " + key + ": " + data[key])

    def make_user(self, data):
        key = "USERNAME"
        user_accept = {"USERNAME_ACCEPTED": False}

        if data[key] not in AsyncServer.transport_map:
            user_accept["USERNAME_ACCEPTED"] = True
            user_accept["INFO"] = "Welcome to the server!"
            self.username = data[key]
            AsyncServer.transport_map[data[key]] = self.thread_transport

            users_online = []
            for user in AsyncServer.transport_map:
                users_online.append(user)

            user_accept["USER_LIST"] = users_online

            message_dump = AsyncServer.messages
            user_accept["MESSAGES"] = message_dump

        else:
            user_accept["USERNAME_ACCEPTED"] = False

        msg = json.dumps(user_accept).encode('ascii')
        self.send_message(msg)

        if user_accept["USERNAME_ACCEPTED"]:
            self.new_user(data[key])
            AsyncServer.all_users_ever_logged.add(data[key])
            

    def new_user(self, username):
        user_message = {"USERS_JOINED": [username]}
        user_message = json.dumps(user_message).encode('ascii')
        self.broadcast("ALL", user_message)

    def handle_messages(self, data):
        msg = {"MESSAGES": []}

        for message in data["MESSAGES"]:
            print(message)
            if message[3].startswith('/'):  
                
                tokenized_message = message[3].split()
                
                if tokenized_message[0] == '/Name':
                    message[3] = "Your username is " + self.username;
                    dm = {"MESSAGES": [message]}
                    dm = json.dumps(dm).encode('ascii')
                    self.broadcast(message[1], dm)
                    
                elif tokenized_message[0] == '/Block':
                    
                    tokenized_message.pop(0)
                    block_users_list = tokenized_message
                    
                    server_message = "The following users will now be blocked: "
                    
                    for user in block_users_list:
                        if user in AsyncServer.all_users_ever_logged and user != self.username:
                            server_message += (" " + user)
                            
                            if self.username in AsyncServer.client_blocked_users:
                                AsyncServer.client_blocked_users[self.username].add(user)
                            else:
                                AsyncServer.client_blocked_users[self.username] = set()
                                AsyncServer.client_blocked_users[self.username].add(user)
                    
                    message[3] = server_message;
                    dm = {"MESSAGES": [message]}
                    dm = json.dumps(dm).encode('ascii')
                    self.broadcast(message[1], dm)
                    
                    
                elif tokenized_message[0] == '/UnBlock':
                    
                    if self.username in AsyncServer.client_blocked_users:
                    
                        tokenized_message.pop(0)
                        
                        unblock_users_set = tokenized_message
                        
                        server_message = "The following users will now be un-blocked: "
                        
                        for user in unblock_users_set:
                            
                            if user in AsyncServer.client_blocked_users[self.username] and user != self.username:
                                server_message += (" " + user)
                                
                                if self.username in AsyncServer.client_blocked_users:
                                    AsyncServer.client_blocked_users = AsyncServer.client_blocked_users[self.username].remove(user)
                        
                        message[3] = server_message;
                        dm = {"MESSAGES": [message]}
                        dm = json.dumps(dm).encode('ascii')
                        self.broadcast(message[1], dm)
                        
                elif tokenized_message[0] == '/Blocked':

                    if self.username in AsyncServer.client_blocked_users and len(AsyncServer.client_blocked_users[self.username]) != 0:
                        blocked_users_set = AsyncServer.client_blocked_users[self.username]
                        server_message = "You currently have these users blocked: " + " ".join(str(user) for user in blocked_users_set)
                        
                    else:
                        server_message = "You have no users blocked"
                        
                    message[3] = server_message
                    dm = {"MESSAGES": [message]}
                    dm = json.dumps(dm).encode('ascii')
                    self.broadcast(message[1], dm)
                        
                elif message[3] == '/DisplayUsers':
                    
                    message[3] = '\n\nCURRENT USER(S) ONLINE\n' + str('-'*22) + '\n' + "\n".join(str(user) for user in AsyncServer.transport_map)
                    dm = {"MESSAGES": [message]}
                    dm = json.dumps(dm).encode('ascii')
                    self.broadcast(message[1], dm)
                    
                    
                elif message[3] == '/DisplayAllUsers':
                    
                    server_message = '\n\n   ALL USER(S)\n' + str('-'*22) + '\n'
                    
                    for user in AsyncServer.all_users_ever_logged:
                        server_message = server_message + '\n' + str(user)
                        
                        if user in AsyncServer.transport_map:
                            server_message = server_message + ' : ONLINE'
                        else:
                            server_message = server_message + ' : OFFLINE'
                            
                    
                    message[3] = server_message
                    dm = {"MESSAGES": [message]}
                    dm = json.dumps(dm).encode('ascii')
                    self.broadcast(message[1], dm)
                    
                else:
                    pass
            elif message[1] == 'ALL':
                print('Testing')
                if ((self.username in AsyncServer.client_blocked_users) and message[0] in AsyncServer.client_blocked_users[self.username]):
                    msg["MESSAGES"].append(message)
                    AsyncServer.messages.append(message)
            else:
                dm = {"MESSAGES": [message]}
                dm = json.dumps(dm).encode('ascii')
                self.broadcast(message[1], dm)

        msg = json.dumps(msg).encode('ascii')
        self.broadcast("ALL", msg)

    def connection_lost(self, exc):
        AsyncServer.transport_map.pop(self.username)
        msg = {"USERS_LEFT": [self.username]}
        msg = json.dumps(msg).encode('ascii')
        self.broadcast("ALL", msg)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Example Server')
    parser.add_argument('host', help='IP or hostname')
    parser.add_argument('-p', metavar='port', type=int, default=9000,
                        help='TCP port (default 9000)')
    args = parser.parse_args()

    loop = asyncio.get_event_loop()

    purpose = ssl.Purpose.CLIENT_AUTH
    context = ssl.create_default_context(purpose, cafile='ca.crt')
    context.load_cert_chain('localhost.pem')

    coro = loop.create_server(AsyncServer, *(args.host, args.p), ssl=context)

    server = loop.run_until_complete(coro)
    print('Listening at {}'.format((args.host, args.p)))



    try:
        loop.run_forever()
    finally:
        server.close()
        loop.close()
