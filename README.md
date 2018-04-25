# Chatterbox
An asyncronous chat server and client written in Python 3.

## Usage
- Clone the project
- Navigate to the project folder in the terminal
- If Running Server:
    - `python server.py localhost -p <port_num>`
- If Running Client:
    - `python client.py <server_addr> -p <port_num>`
    - NOTE: When connecting to localhost use `-ca ca.crt` with the client call, with servers that have verified ca files this is unnecessary

### Client Interaction
The client will ask for a username, and depending on the availability of said username may ask for a different username.
Once the username has been established, the client will display all users online and past messages.
At this point the user is free to type any message and send it to the chat server.
- Prefixing a message with `@<username> ` will send a direct message to that user if they are online. Remember to put a space between the username and the message.
Any updates on the server, logins, logouts, new messages, etc., will be automatically displayed on the client's screen as they come

#### Additional Client Commands
- `/Name` - returns client's username
- `/Block <username>` - blocks messages to and from the specified username
- `/UnBlock <username>` - unblocks messages from the specified username
    - Note: if the unblocked user has blocked the current client, messages still cannot be sent between the two clients
- `/Blocked` - display all users whom the client has blocked
- `/DisplayUsers` - display all currently active users
- `/DisplayAllUsers` - display all users whom have ever been active

## Additional Specs & Information
- All data from the server are stored to a flat file database system, pickle
- All data sent between the client and server are encrypted using tls
- All client interaction is handled asynchronously from the incoming data using the Asyncio library and coroutines
- This project is licensed using the [GNU General Public License](https://www.gnu.org/licenses/gpl-3.0.en.html)

## Original Creators
- [codeWonderland](https://github.com/codeWonderland)
- [EricCacciavillani](https://github.com/EricCacciavillani)

## Original Assignment
Problem Statement

For your final project you will be implementing asynchronous client and server code for a chat program that will operate over a secure TLS connection over TCP sockets.  It is recommended that you get this working entirely unencrypted first, before moving on to make this work with TLS.

 

You may work on the project individually or in pairs, but if working in pairs be sure to document this in your headers and make sure both partners submit on Canvas!

You should be sure to follow the requirements of the protocol exactly so that your client can connect to other students' server and vice-versa.

The basic protocol that this program will follow is sending JSON messages over TCP sockets prefixed by the message length (complete length of JSON message) encoded as 4 byte unsigned integer (this will allow sending very long messages, much longer than will be needed in a typical chat exchange, but allow for flexibility in the future). 

Client

Connecting will involve a user connecting to the server, and then providing a username in the form of

`'{"USERNAME": "user1"}'`

where `user1` is the username the user has chosen.

If this username is already in use then the server should respond with a message indicating this.  This response should take the form

`'{"USERNAME_ACCEPTED": true}'` or `'{"USERNAME_ACCEPTED": false}'`

if that username is accepted or not.  These messages might also contain additional info, such as

`'{"USERNAME_ACCEPTED": false, "INFO": "The provided username is already in use."}'`

When the username is accepted, the response should also contain

(a) USER_LIST, which is a list of all usernames currently in the chat session, and

(b) MESSAGES, which is a list of previous public messages and private messages to this specific user (see below) since the server has been running (this might get long in practice, but we won't be running these servers forever). 

`'{"USERNAME_ACCEPTED": true, "INFO": "Welcome!", "USER_LIST": ["user1", "user2", "user3"], "MESSAGES": [MESSAGE1, MESSAGE2,...]}'`

Where `MESSAGE1`, `MESSAGE2`, ... are message entries sorted from oldest to newest.  See below for details of each message entry.

Once in the connected state, the client will be asynchronously receiving inputs from the user and new messages from the server.  Messages from the client -> server can be of two forms: broadcasts to all users and private messages to individual users.  How you choose to differentiate this in your interface is up to you (one way would be to have messages default to sending to all, and optionally prefix with `@username` to send direct one other user).  The protocol for messages should be as follows:

`'{"MESSAGES": [MESSAGE1, MESSAGE2,...]}'`

as above (note: multiple messages may always come at one), where each message is a 4-tuple:

(SRC, DEST, TIMESTAMP, CONTENT)

SRC is a string containing the sender's username
DEST is a string containing either "ALL" or destination username (for private messages)
TIMESTAMP is an integer timestamp containing seconds since epoch in UTC (note this is an integer, but is JSON so will be coming across as text like the rest).
CONTENT is a string containing the message content
The other commands that the client can receive from the server are USERS_JOINED and USERS_LEFT messages, where USERS_JOINED is a list of new usernames (Sent when someone else joined the room), and USERS_LEFT is a list of usernames of users that have left the room.

Note: All of these types of information can piggy-back on top of each other, so a single json message might contain 1 or more of these instructions.

Finally the user can quit the chat room, which should close the connection (and will therefore notify the server that they have left).

Any error or unexpected message from the user should display appropriate info to the user.

Server
The server must handle all of these events. 

It must handle users joining by checking if their provided name is available and sending the appropriate response (see above), as well as notifying all other users that they have joined the room. 
It must handle users sending messages and directing these to the proper destination (depending on if going to all users or privately). 
As part of sending messages, it must verify that the SRC field matches the username that is connected on that socket, and send an error message back if not
It must handle users leaving the room (seeing they have closed their connection) and notifying other users. 
And, it must handle keeping track of message history that it can provide to new users when they join.
Finally, if an invalid message is received the server should respond with an error message

`'{"ERROR": "Details of error message"}'`

which the client should then display to the user.

---------------------

How you implement the user interface is up to you, as long as you follow the protocols as described.  Up to 10% bonus point will be awarded for especially nice interfaces, but I strongly advise you to get the basic architecture working first!

An additional 20% bonus point will be awarded for other features.  To receive these you must provide a separate document describing these features (as a pdf file).  These may not break the rest of the protocol, but can be things that only work with your specific client and server (in which case you will want to send extra information when connecting to make the server aware you support a particular feature). 

Example enhancements (not all are equally valuable, number of bonus points will be based on degree of difficulty and how well they are implemented and documented):

A file transfer mechanism.
Support for compressing messages in transit.
Remembering what IP is associated with a username and not letting someone else use that username for some time.
Persistent storage of chat history so it will be maintained across server restarts.
Other things you may think of.
 

You will upload all code (and documentation for bonus) in a single zip file to canvas.

 

Additional Requirements
You must include proper docstrings on your modules, classes, and functions/methods
You must follow PEP8 style.
You must use the results of getaddrinfo when connecting and binding rather than hardcoding values.
The client interface must display messages to the user and asynchronously handle receiving user input as well as messages from the server
