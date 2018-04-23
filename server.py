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

    def connection_made(self, transport):
        self.transport = transport

    def send_message(self, data):
        self.transport.write(struct.pack("!I", len(data)))
        self.transport.write(data)

    def data_received(self, data):
        if self.__buffer == "":
            data_len = struct.unpack("!I", data[0:4])[0]
            data = data.decode('ascii')
            data = data[4:(data_len + 4)]
        else:
            data = data.decode('ascii')

        if data[0] == '{':
            self.__buffer = data
        else:
            self.__buffer += data

        if data[-1] == '}':
            data = json.loads(self.__buffer)
            self.__buffer = ''

            for key in data:
                if key == "USERNAME":
                    user_accept = {"USERNAME_ACCEPTED": False}
                    if data[key] not in self.userlist:
                        user_accept["USERNAME_ACCEPTED"] = True
                        user_accept["INFO"] = "Welcome to the server!"
                        self.userlist.append(data[key])

                        self.new_user(data[key])
                    else:
                        user_accept["USERNAME_ACCEPTED"] = False

                    user_accept = json.dumps(user_accept).encode('ascii')
                    self.send_message(user_accept)

                elif key == "MESSAGES":
                    for message in data[key]:
                        print(message[0] + ": " + message[3])

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
