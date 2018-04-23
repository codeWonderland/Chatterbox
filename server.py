#!/usr/bin/env python3
# Foundations of Python Network Programming, Third Edition
# https://github.com/brandon-rhodes/fopnp/blob/m/py3/chapter07/srv_asyncio2.py
# Asynchronous I/O inside an "asyncio" coroutine.

# Last modified by Alice Easter && Eric Cacciavillani on 4/6/18
import json

import argparse
import asyncio
import struct


class AsyncServer(asyncio.Protocol):
    def __init__(self):
        super().__init__()
        self.userlist = []
        self.__buffer = ""
        self.data_len = 0

    def connection_made(self, transport):
        self.transport = transport

    def send_message(self, data):
        msg = b''
        msg += struct.pack("!I", len(data))
        msg += data
        self.transport.write(msg)

    def broadcast(self, data):
        # TODO: Figure out how to broadcast to all users
        self.send_message(data)

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
                    user_accept = {"USERNAME_ACCEPTED": False}
                    if data[key] not in self.userlist:
                        user_accept["USERNAME_ACCEPTED"] = True
                        user_accept["INFO"] = "Welcome to the server!"
                        self.userlist.append(data[key])
                    else:
                        user_accept["USERNAME_ACCEPTED"] = False

                    msg = json.dumps(user_accept).encode('ascii')
                    self.send_message(msg)

                    if user_accept["USERNAME_ACCEPTED"]:
                        self.new_user(data[key])

                elif key == "MESSAGES":
                    msg = {"MESSAGES": []}
                    for message in data[key]:
                        print(message[0] + ": " + message[3])
                        msg["MESSAGES"].append(message)

                    msg = json.dumps(msg).encode('ascii')
                    self.broadcast(msg)

                else:
                    print("New message type!!! " + key + ": " + data[key])

    def new_user(self, username):
        user_message = {"USERS_JOINED": [username]}
        user_message = json.dumps(user_message).encode('ascii')
        self.send_message(user_message)

    def connection_lost(self, exc):
        print(exc)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Example Server')
    parser.add_argument('host', help='IP or hostname')
    parser.add_argument('-p', metavar='port', type=int, default=9000,
                        help='TCP port (default 9000)')
    args = parser.parse_args()

    loop = asyncio.get_event_loop()

    coro = loop.create_server(AsyncServer, *(args.host, args.p))

    server = loop.run_until_complete(coro)
    print('Listening at {}'.format((args.host, args.p)))



    try:
        loop.run_forever()
    finally:
        server.close()
        loop.close()
