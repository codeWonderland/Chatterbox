"""async_client

Champlain College CSI-235, Spring 2018
Prof. Josh Auerbach

Bare bones example of asynchronously receiving
data from server and user input from stdin
"""
import argparse
import asyncio


class AsyncClient(asyncio.Protocol):

    def data_received(self, data):
        """simply prints any data that is received"""
        print("received: ", data)


@asyncio.coroutine
def handle_user_input(loop):
    """reads from stdin in separate thread

    if user inputs 'quit' stops the event loop
    otherwise just echos user input
    """
    while True:
        message = yield from loop.run_in_executor(None, input, "> ")
        if message == "quit":
            loop.stop()
            return
        print(message)


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
    asyncio.async(handle_user_input(loop))

    try:
        loop.run_forever()
    finally:
        loop.close()
