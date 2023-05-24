import asyncio
import aiohttp
import hashlib
import collections
import time
import datetime
import base64
from textwrap import wrap
import argparse

# Create the parser
parser = argparse.ArgumentParser(description="TCP Server")

# Add the arguments
parser.add_argument('--escape-char', type=str, help='Escape character', required=True)
parser.add_argument('--webhook-url', type=str, help='Webhook URL', required=True)
parser.add_argument('--port', type=int, help='Port to listen on', required=True)
parser.add_argument('--ack-string', type=str, help='Acknowledgement string or "from_webhook"', required=True)

# Parse the arguments
args = parser.parse_args()

# Check if the escape character is the string "\n", if so replace it with the actual newline character
if args.escape_char == "\\n":
    args.escape_char = "\n"

ESCAPE_CHAR = args.escape_char.encode()  # make it bytes since we're checking against bytes
URL = args.webhook_url
PORT = args.port
ACK = args.ack_string

clients = collections.defaultdict(lambda :{"message": b"", "timestamp": time.time()})

now = lambda :datetime.datetime.now().isoformat()

def generate_hash_client(addr):
    return hashlib.sha1('{}-{}'.format(*addr).encode()).hexdigest()

async def send_to_ubifunction(payload, hash_client):
    payload.update({'hash': hash_client})
    print("[{}] SENDING DATA: {}".format(now(), len(payload)))

    async with aiohttp.ClientSession() as session:
        async with session.post(URL, json=payload) as resp:
            data = await resp.json()
            print("Response: {} status:{}".format(data, resp.status))
            if ACK == "from_webhook":
                return data.get('response', data.get('error','data received'))
            return ACK

class EchoServerProtocol(asyncio.Protocol):
    def connection_made(self, transport):
        self.peername = transport.get_extra_info('peername')
        print('Connection from {}'.format(self.peername))
        self.transport = transport

    def data_received(self, data):
        loop = asyncio.get_event_loop()
        loop.create_task(self.handle_income_packet(data))

    async def handle_income_packet(self, data):
        hash_client = generate_hash_client(self.peername)
        try:
            message = data.decode('utf-8')  # Try to decode the data as text
            is_text = True
        except UnicodeDecodeError:  # If this fails, it's probably bytes
            message = " ".join(wrap(data.hex(), 2))  # We'll keep your hex representation here
            is_text = False

        print('[{}] Received {} from {}'.format(now(), message, self.peername))
        print('[{}] Data received: {!r}'.format(now(), message))
        if ESCAPE_CHAR in data:
            if is_text:
                message = message.rstrip("\n") # strip out newline character
                payload = {'data': message, 'event': 'data'}
            else:
                payload = {'data': base64.b64encode(data).decode(), 'event': 'data'}
            ACK = await send_to_ubifunction(payload, hash_client)
            self.transport.write(ACK if isinstance(ACK, bytes) else ACK.encode())


loop = asyncio.get_event_loop()

tcp_server = loop.create_server(EchoServerProtocol, '0.0.0.0', PORT)
server = loop.run_until_complete(tcp_server)

print('Serving on TCP')


try:
    loop.run_forever()
except KeyboardInterrupt:
    pass

# Close the server
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()
