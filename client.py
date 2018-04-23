"""async_client
Champlain College CSI-235, Spring 2018
Prof. Josh Auerbach
Bare bones example of asynchronously receiving
data from server and user input from stdin
"""
import json
import struct
import time

import argparse
import asyncio


class AsyncClient(asyncio.Protocol):
    def __init__(self):
        self.__buffer = ""
        self.is_logged_in = False
        self.username = ""
        self.data_len = 0

    def connection_made(self, transport):
        self.transport = transport
        self.is_logged_in = False

    def send_message(self, data):
        msg = b''
        msg += struct.pack("!I", len(data))
        msg += data
        self.transport.write(msg)

    def data_received(self, data):
        """simply prints any data that is received"""
        # get data into usable format
        if self.__buffer == '':
            # Find first brace and offset the data by that
            brace_index = data.find(b'{')
            self.data_len = struct.unpack("!I", data[0:brace_index])[0]
            data = data[brace_index:(self.data_len + brace_index)]

        data = data.decode('ascii')

        self.__buffer += data

        if len(self.__buffer) == self.data_len:
            data = json.loads(self.__buffer)
            self.__buffer = ''
            self.data_len = 0

            for key in data:
                if key == "USERNAME_ACCEPTED":
                    if data[key]:
                        self.is_logged_in = True
                        print('\nSuccessfully Logged In')
                elif key == "INFO":
                    print(data[key])
                    print()
                elif key == "USER_LIST":
                    print("USERS ONLINE:")
                    for value in data[key]:
                        if value is not '':
                            print(value)
                    print()
                elif key == "MESSAGES":
                    for message in data[key]:
                        if message[1] == "ALL" or message[1] == self.username:
                            print(message[0] + ": " + message[3])
                elif key == "USERS_JOINED":
                    print("New User(s) Joined:")
                    for user in data[key]:
                        print(user)
                    print()
                elif key == "USERS_LEFT":
                    print("User(s) Left:")
                    for user in data[key]:
                        print(user)
                    print()
                # Encapsulates error and other servers' additional features
                else:
                    print(key + ": " + data[key])


@asyncio.coroutine
def handle_user_input(loop, client):
    """reads from stdin in separate thread
    if user inputs 'quit' stops the event loop
    otherwise just echos user input
    """
    while not client.is_logged_in:
        login_data = {"USERNAME": ""}

        message = yield from loop.run_in_executor(None, input, "> Enter your username:  ")
        if message == "quit":
            loop.stop()
            return

        client.username = message
        login_data["USERNAME"] = message
        data_json = json.dumps(login_data)
        data_bytes_json = data_json.encode('ascii')

        client.send_message(data_bytes_json)

        yield from asyncio.sleep(1)

    while client.is_logged_in:
        recip = "ALL"
        message = yield from loop.run_in_executor(None, input, "> ")
        if message == "quit":
            loop.stop()
            return

        # Checking for DM
        if len(message) != 0 and message[0] == '@':
            index = message.find(' ')
            recip = message[1:index]
            message = message[index + 1:]

        message = {"MESSAGES": [(client.username, recip, int(time.time()), message)]}
        message = json.dumps(message)
        message = message.encode('ascii')
        client.send_message(message)

        yield from asyncio.sleep(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Example client')
    parser.add_argument('host', help='IP or hostname')
    parser.add_argument('-p', metavar='port', type=int, default=9000,
                        help='TCP port (default 9000)')
    args = parser.parse_args()

    loop = asyncio.get_event_loop()

    # we only need one client instance
    client = AsyncClient()

    # the lambda client serves as a factory that just returns
    # the client instance we just created
    coro = loop.create_connection(lambda: client, args.host, args.p)

    loop.run_until_complete(coro)

    # Start a task which reads from standard input
    asyncio.async(handle_user_input(loop, client))


    try:
        loop.run_forever()
    finally:
        loop.close()
