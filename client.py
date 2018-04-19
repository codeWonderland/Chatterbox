import sys
import socket
import argparse
import json
from threading import Thread

"""
>>> data = 'abcdefg'
>>> [delim for delim in ('a', 'e') if delim in data]
['a', 'e']
"""

"""client.py

Last modified by Alice Easter && Eric Cacciavillani on 4/6/18

Champlain College CSI-235, Spring 2018
This code builds off skeleton code written by 
Prof. Joshua Auerbach (jauerbach@champlain.edu)
"""

RESPONSE_DELIMITERS = [b'.', b'!']

MAX_BYTES = 1024


class ChatClient:
    def __init__(self, host, port):
        self.__buffer = b''
        self.username = ''
        need_username = True
        # getaddrinfo functionality replicated from
        # https://github.com/brandon-rhodes/fopnp/blob/m/py3/chapter04/www_ping.py

        try:
            info_list = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM, 0, socket.AI_ADDRCONFIG | socket.AI_V4MAPPED)

        except socket.gaierror as e:
            print('Failure in getaddrinfo: ', e.args[1])
            sys.exit(1)

        info = info_list[0]
        socket_args = info[0:3]
        address = info[4]
        self.sock = socket.socket(*socket_args)

        try:
            self.sock.connect(address)

        except socket.error as e:
            print('Network failure: ', e.args[1])
            sys.exit(1)

        else:
            print('Successfully connected to host', info[4][0], 'is listening on port', info[4][1])

            while need_username:
                # Get username
                self.username = input('Please provide a username: ')

                # TODO: We aren't getting a response so we probably aren't sending the data right
                self.sock.sendall(self.username.encode('ascii'))

                # Check to see if username is available
                resp = json.loads(self.sock.recv(MAX_BYTES).decode('ascii'))

                if resp['USERNAME_ACCEPTED'] == 'true':
                    print('Username valid, welcome to the chat server')
                    need_username = False
                else:
                    print('Username invalid')

                    # If the server responded with extra info we print it
                    if 'INFO' in resp:
                        print(resp['INFO'])

    def recv_until_delimiters(self, delim_list, buffer_size=1024):
        """ note, make sure this
            -returns the message up to and including the FIRST delimiter
               regardless of the order of the delimiters in the delimiters list
               -so even if delimiters is [b'.', b'!'] and we recv b"Yes!No."
               -should return b"Yes!" and store b"No." in a buffer
        """
        data = b''
        delim_dict = {}
        lowest_index = 10000  # Arbitrary value that is too high to be the length of a string

        if self.__buffer is not None:
            for key in delim_list:
                delim_dict[key] = self.__buffer.find(key)

                if delim_dict[key] != -1 and delim_dict[key] < lowest_index:
                    lowest_index = delim_dict[key]

            if lowest_index < 10000:
                data += self.__buffer[0:lowest_index + 1]
                self.__buffer = self.__buffer[lowest_index + 1:]
                return data

            else:
                data += self.__buffer
                self.__buffer = b''

        while True:
            resp = self.sock.recv(MAX_BYTES)
            delim_dict = {}
            lowest_index = 10000  # Arbitrary value that is too high to be the length of a string

            for key in delim_list:
                delim_dict[key] = resp.find(key)

                if delim_dict[key] != -1 and delim_dict[key] < lowest_index:
                    lowest_index = delim_dict[key]

            if lowest_index < 10000:
                data += resp[0:lowest_index + 1]
                self.__buffer = resp[lowest_index + 1:]
                return data

            data += resp

    def ask_question(self, question):
        self.sock.sendall(question.encode('ascii'))

    def recv_next_response(self):
        """receives the next available question response"""
        return self.recv_until_delimiters()

    def close(self):
        self.sock.close()

    def __del__(self):
        self.sock.close()


def run_interactive_client(host, port):
    client = ChatClient(host, port)
    print('Enter your questions')
    print('Enter q to exit')
    print('End all questions with only one ?')
    while True:
        question = input('>>> ')
        if question == 'q':
            exit(1)
        if question.endswith('?') and len(question.split('?')) > 1:
            client.ask_question(question)
            print(client.recv_next_response().decode('ascii'))
            print()
        else:
            print('ERROR: No or multiple question marks received')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Example client')
    parser.add_argument('host', help='IP or hostname')
    parser.add_argument('-p', metavar='port', type=int, default=7000,
                        help='TCP port (default 7000)')
    args = parser.parse_args()
    run_interactive_client(args.host, args.p)
