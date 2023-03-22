import socket
import threading
import requests
import argparse

def parse_arguments():
    parser = argparse.ArgumentParser(description="TCP server that sends data to a webhook")
    parser.add_argument("--webhook-url", type=str, required=True, help="Webhook URL to send data")
    parser.add_argument("--port", type=int, default=5555, help="Port to listen on (default: 5555)")
    parser.add_argument("--escape-char", type=str, default="#", help="Escape character (default: '#')")
    return parser.parse_args()

def handle_client(client_socket, addr, webhook_url, escape_char):
    print(f"[+] Connection from {addr}")

    data_buffer = ""

    while True:
        # Receive data from the client
        data = client_socket.recv(1024).decode("utf-8")

        if not data:
            break

        # Check for the escape character in the received data
        for char in data:
            if char == escape_char:
                # Send the accumulated data to the webhook
                try:
                    response = requests.post(webhook_url, json={"data": data_buffer})
                    status_code = response.status_code

                    if 200 <= status_code < 300:
                        client_socket.sendall(b"ok")
                        print(f"[+] Data sent to webhook: {data_buffer}")
                    elif 400 <= status_code < 500:
                        client_socket.sendall(b"error")
                        print(f"[-] Error: webhook returned status code {status_code}")

                except Exception as e:
                    print(f"[-] Error sending data to webhook: {e}")
                finally:
                    # Reset the buffer after sending the data
                    data_buffer = ""
            else:
                data_buffer += char

    print(f"[-] Connection closed: {addr}")
    client_socket.close()

def main():
    args = parse_arguments()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", args.port))
    server.listen(5)
    print(f"[*] Listening on 0.0.0.0:{args.port}")

    while True:
        client, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(client, addr, args.webhook_url, args.escape_char))
        thread.start()

if __name__ == "__main__":
    main()
