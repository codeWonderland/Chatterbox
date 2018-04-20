#!/usr/bin/env python3
# Foundations of Python Network Programming, Third Edition
# https://github.com/brandon-rhodes/fopnp/blob/m/py3/chapter07/srv_asyncio2.py
# Asynchronous I/O inside an "asyncio" coroutine.

# Last modified by Alice Easter && Eric Cacciavillani on 4/6/18

import asyncio
import zen_utils

import random

SERVER_RESPONSES = [b"It is certain.", b"It is decidedly so.",
                    b"Without a doubt!", b"Yes definitely.",
                    b"You may rely on it!", b"As I see it, yes.",
                    b"Most likely.", b"Outlook good!",
                    b"Yes!", b"Signs point to yes!",
                    b"Reply hazy try again.", b"Ask again later!",
                    b"Better not tell you now!", b"Cannot predict now.",
                    b"Concentrate and ask again.", b"Don't count on it.",
                    b"My reply is no!", b"My sources say no.",
                    b"Outlook not so good!", b"Very doubtful."]


@asyncio.coroutine
def handle_conversation(reader, writer):
    address = writer.get_extra_info('peername')
    print('Accepted connection from {}'.format(address))
    try:
        while True:
            data = b''
            while not data.endswith(b'?'):
                more_data = yield from reader.read(4096)
                if not more_data:
                    if data:
                        print('Client {} sent {!r} but then closed'
                              .format(address, data))
                    else:
                        print('Client {} closed socket normally'.format(address))
                    return
                data += more_data
            answer = SERVER_RESPONSES[random.randint(0, 19)]
            writer.write(answer)

    except ...:
        print('Error in handle_conversation()')
        return


if __name__ == '__main__':
    address = zen_utils.parse_command_line('asyncio server using coroutine')
    loop = asyncio.get_event_loop()
    coro = asyncio.start_server(handle_conversation, *address)
    server = loop.run_until_complete(coro)
    print('Listening at {}'.format(address))
    try:
        loop.run_forever()
    finally:
        server.close()
        loop.close()
