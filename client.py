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
        self.processing_data = False
        self.__buffer = ""
        self.is_logged_in = False
        self.username = ""

    def connection_made(self, transport):
        self.transport = transport
        self.is_logged_in = False

    def send_message(self, length, data):
        self.transport.write(length)
        self.transport.write(data)

    def data_received(self, data):
        """simply prints any data that is received"""
        # get data into usable format
        data_len = 0

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
                if key == "USERNAME_ACCEPTED":
                    if data[key]:
                        self.is_logged_in = True
                        print('\nSuccessfully Logged In')
                    else:
                        self.processing_data = False
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


@asyncio.coroutine
def handle_user_input(loop, client):
    """reads from stdin in separate thread
    if user inputs 'quit' stops the event loop
    otherwise just echos user input
    """
    while not client.is_logged_in:
        if not client.processing_data:
            login_data = {"USERNAME": ""}

            message = yield from loop.run_in_executor(None, input, "> Enter your username:  ")
            if message == "quit":
                loop.stop()
                return

            client.username = message
            login_data["USERNAME"] = message
            data_json = json.dumps(login_data)
            data_bytes_json = data_json.encode('ascii')
            byte_count = struct.pack("!I", len(data_bytes_json))

            # The idea is we stop the client from asking for the username again until we determine if they are logged in
            client.processing_data = True
            client.send_message(byte_count, data_bytes_json)

        yield from asyncio.sleep(5)

    while client.is_logged_in:
        message = yield from loop.run_in_executor(None, input, "> ")
        if message == "quit":
            loop.stop()
            return
        client.send_message(struct.pack("!I", len(message)), message)


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