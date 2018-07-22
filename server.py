#!/usr/bin/env python3
# Foundations of Python Network Programming, Third Edition
# https://github.com/brandon-rhodes/fopnp/blob/m/py3/chapter07/srv_asyncio2.py
# Asynchronous I/O inside an "asyncio" coroutine.

# Last modified by Alice Easter && Eric Cacciavillani on 4/26/18
import json

import argparse
import asyncio
import ssl
import struct
import pickle
from collections import defaultdict



class AsyncServer(asyncio.Protocol):
    transport_map = {}  # Map of usernames to transports
    messages = []  # All messages for dump to user upon login
    all_users_ever_logged = set()  # Init a set of all users ever logged into the server
    client_blocked_users = defaultdict(dict)  # Shows the relationship between given users and their blocked user names

    def __init__(self):
        super().__init__()
        self.username = ""

        # Establish the user associated with this object
        self.thread_transport = None

        '''
        Since we need to send message to individual user, we have a modifiable
        current transport that we can use to determine the recipient of any
        given message
        '''
        self.current_transport = None
        self.__buffer = ""
        self.data_len = 0

        #Pull data from db upon client init
        with open('server_data.pkl', 'rb') as f:
            AsyncServer.messages = pickle.load(f)
            AsyncServer.all_users_ever_logged = pickle.load(f)
            AsyncServer.client_blocked_users = pickle.load(f)

        if AsyncServer.client_blocked_users is None:
            AsyncServer.client_blocked_users = defaultdict(dict)

        if AsyncServer.messages is None:
            AsyncServer.messages = list()

        if AsyncServer.all_users_ever_logged is None:
            AsyncServer.all_users_ever_logged = set()

    def connection_made(self, transport):
        self.thread_transport = transport
        self.current_transport = transport

    # Pre: current transport should be set to the proper audience and data is
    #       already in json format and encoded to ascii
    # Post: sends data to the current transport
    # Purpose: packs the size of the data, prepends said size to the data, then
    #       sends the message through the current transport
    def send_message(self, data):
        msg = b''
        msg += struct.pack("!I", len(data))
        msg += data
        self.current_transport.write(msg)

    # Sends data to intended audience with the qualifier that said audience
    # isn't blocked and haven't blocked this user
    def broadcast(self, audience, data):

        # Sending messages to themselves
        if audience is self.username:
            self.current_transport = self.thread_transport
            self.send_message(data)

        # Send messages to all users logged into the system
        elif audience == 'ALL':
            for user in AsyncServer.transport_map:

                # Ensures user messages to be properly blocked
                if AsyncServer.client_blocked_users is not None and self.username in AsyncServer.client_blocked_users:

                    if AsyncServer.client_blocked_users[self.username] is not None and user not in AsyncServer.client_blocked_users[self.username]:
                        self.current_transport = AsyncServer.transport_map[user]
                        self.send_message(data)

                # ----
                elif AsyncServer.client_blocked_users is not None and user in AsyncServer.client_blocked_users:

                    if AsyncServer.client_blocked_users[user] is not None and self.username not in AsyncServer.client_blocked_users[user]:
                        self.current_transport = AsyncServer.transport_map[user]
                        self.send_message(data)

                else:
                    self.current_transport = AsyncServer.transport_map[user]
                    self.send_message(data)

        # If we are sending a dm
        elif audience in AsyncServer.transport_map:

            # Ensures user messages to be properly blocked
            if AsyncServer.client_blocked_users is not None and audience in AsyncServer.client_blocked_users:

                if AsyncServer.client_blocked_users[audience] is not None and self.username not in AsyncServer.client_blocked_users[audience]:
                    self.current_transport = AsyncServer.transport_map[audience]
                    self.send_message(data)
            # -----
            elif AsyncServer.client_blocked_users is not None and self.username in AsyncServer.client_blocked_users:

                if AsyncServer.client_blocked_users[self.username] is not None and audience not in AsyncServer.client_blocked_users[self.username]:
                    self.current_transport = AsyncServer.transport_map[audience]
                    self.send_message(data)

            else:
                self.current_transport = AsyncServer.transport_map[audience]
                self.send_message(data)

        # Would be called if the message is to an audience that doesn't exist
        else:
            self.current_transport = self.thread_transport
            msg = {"ERROR": "Specified username does not exist (or at least is not online)"}
            msg = json.dumps(msg).encode('ascii')
            self.send_message(msg)

    # Handles all data recived from
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

            # We have two types of accepted keys, usernames and messages
            # If we receive anything else we want to recognize it so we
            # Output it to the server console, otherwise we direct the data
            # To the proper management function
            for key in data:
                if key == "USERNAME":
                    self.make_user(data)

                elif key == "MESSAGES":
                    self.handle_messages(data)

                else:
                    print("New message type!!! " + key + ": " + data[key])

    # Pre: Takes in a username
    # Post: Returns username accepted status, and optionally updates user with
    #       Past messages
    # Purpose: Determines if the username is currently in use, if it is then
    #       we notify the client, if not we add them to the class's static
    #       transports variable notify them that they are logged in,  send them
    #       all previous message data, and notify other users that the new user
    #       has joined the server
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

            user_accept["USER_LIST"] = self.get_users()

            message_dump = AsyncServer.messages

            if AsyncServer.client_blocked_users is not None and self.username in AsyncServer.client_blocked_users:
                message_dump = list(
                    filter(lambda message: message[0] not in AsyncServer.client_blocked_users[self.username],
                           message_dump))

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

    # Gets an array of user objects
    def get_users(self):
        userlist = []

        for username in self.all_users_ever_logged:
            userlist.append({
                "name" : username,
                "active" : False
            })
        
        for username in AsyncServer.transport_map:
            for user in userlist:
                if user["name"] == username:
                    user["active"] = True 

        return userlist

    # Determines if message is a command then handles it accordingly
    def handle_messages(self, data):
        msg = {"MESSAGES": []}

        for message in data["MESSAGES"]:
            print(message)

            # Possible command found
            if message[3].startswith('/'):

                tokenized_message = message[3].split()

                # COMMAND: /Name
                # FUNCTION: returns client's username
                if tokenized_message[0] == '/Name':
                    message[3] = "Your username is " + self.username;
                    dm = {"MESSAGES": [message]}
                    dm = json.dumps(dm).encode('ascii')
                    self.broadcast(message[1], dm)

                # COMMAND: /Block <username>
                # FUNCTION: blocks messages to and from the specified username
                elif tokenized_message[0] == '/Block':

                    tokenized_message.pop(0)
                    block_users_list = tokenized_message

                    server_message = "The following users will now be blocked: "

                    for user in block_users_list:
                        if user in AsyncServer.all_users_ever_logged and user != self.username:
                            server_message += (" " + user)

                            if AsyncServer.client_blocked_users is not None and self.username in AsyncServer.client_blocked_users:
                                AsyncServer.client_blocked_users[self.username].add(user)
                            else:

                                print(type(AsyncServer.client_blocked_users))
                                AsyncServer.client_blocked_users[self.username]
                                AsyncServer.client_blocked_users[self.username] = set()
                                AsyncServer.client_blocked_users[self.username].add(user)
                                print("Set ", AsyncServer.client_blocked_users[self.username])

                    message[3] = server_message
                    dm = {"MESSAGES": [message]}
                    dm = json.dumps(dm).encode('ascii')
                    self.broadcast(message[1], dm)

                # COMMAND: /UnBlock <username>
                # FUNCTION: unblocks messages from the specified username
                # NOTE: if the unblocked user has blocked the current client
                #       messages still cannot be sent between the two clients
                elif tokenized_message[0] == '/UnBlock':

                    if self.username in AsyncServer.client_blocked_users:

                        tokenized_message.pop(0)

                        unblock_users_set = tokenized_message

                        server_message = "The following users will now be un-blocked: "

                        for user in unblock_users_set:

                            if user in AsyncServer.client_blocked_users[self.username] and user != self.username:
                                server_message += (" " + user)

                                if self.username in AsyncServer.client_blocked_users:
                                    AsyncServer.client_blocked_users = AsyncServer.client_blocked_users[self.username] \
                                        .remove(user)

                        message[3] = server_message
                        dm = {"MESSAGES": [message]}
                        dm = json.dumps(dm).encode('ascii')
                        self.broadcast(message[0], dm)

                # COMMAND: /Blocked
                # FUNCTION: shows all users whom the client has blocked
                elif tokenized_message[0] == '/Blocked':

                    if AsyncServer.client_blocked_users is not None and \
                            self.username in AsyncServer.client_blocked_users and \
                            len(AsyncServer.client_blocked_users[self.username]) != 0:
                        blocked_users_set = AsyncServer.client_blocked_users[self.username]
                        server_message = "You currently have these users blocked: " + " ".join(
                            str(user) for user in blocked_users_set)

                    else:
                        server_message = "You have no users blocked"

                    message[3] = server_message
                    dm = {"MESSAGES": [message]}
                    dm = json.dumps(dm).encode('ascii')
                    self.broadcast(message[1], dm)

                # COMMAND: /DisplayUsers
                # FUNCTION: Display all currently active users
                elif message[3] == '/DisplayUsers':

                    message[3] = '\n\nCURRENT USER(S) ONLINE\n' + str('-' * 22) + '\n' + "\n".join(
                        str(user) for user in AsyncServer.transport_map)
                    dm = {"MESSAGES": [message]}
                    dm = json.dumps(dm).encode('ascii')
                    self.broadcast(message[1], dm)

                # COMMAND: /DisplayAllUsers
                # FUNCTION: Display all users who have ever accessed the server
                elif message[3] == '/DisplayAllUsers':

                    server_message = '\n\n   ALL USER(S)\n' + str('-' * 22) + '\n'

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

            # Those messages that are directed to all get appended to the
            # Monolithic message
            elif message[1] == 'ALL':
                msg["MESSAGES"].append(message)
                AsyncServer.messages.append(message)

            # If a message is directed to a specific user we pull it out of the
            # list of messages and send it to the designated client
            else:
                dm = {"MESSAGES": [message]}
                dm = json.dumps(dm).encode('ascii')
                self.broadcast(message[1], dm)

        msg = json.dumps(msg).encode('ascii')
        self.broadcast("ALL", msg)

    # Remove client from the transport list upon connection lost and backup
    # data to the db
    def connection_lost(self, exc):
        # Check to make sure that the user is logged in
        if (self.username != None && self.username != ''):
            AsyncServer.transport_map.pop(self.username)
            msg = {"USERS_LEFT": [self.username]}
            msg = json.dumps(msg).encode('ascii')
            self.broadcast("ALL", msg)

            with open('server_data.pkl', 'wb') as f:
                pickle.dump(AsyncServer.messages, f)
                pickle.dump(AsyncServer.all_users_ever_logged, f)
                pickle.dump(AsyncServer.client_blocked_users, f)


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
