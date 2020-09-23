#!/usr/bin/env python3
import asyncio
import socket

HOST = 'example.com'
PORT = 80

msg = f"""GET / HTTP/1.1
HOST: {HOST}

""".encode("ascii")

print(f"We are going to send: {msg}")


async def receive(sock):
    send(sock, msg)
    response = sock.recv(500).decode("ascii")
    print(response)


def send(sock, msg):
    i = 0
    m_len = len(msg)
    while i < m_len:
        c_amount = int(input(f"[{i}/{m_len}] Send how many characters? "))
        # if we exceed m_len with given c_amount, set c_amount to characters left
        if c_amount + i > m_len:
            c_amount = m_len - i
        send_msg = msg[i:i+c_amount]
        i += c_amount

        print(f"Sending: {send_msg}")
        print(f"Send so far: {msg[:i]}")
        sock.sendall(send_msg)


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.connect((HOST, PORT))
    loop = asyncio.get_event_loop()
    loop.create_task(receive(sock))
    loop.run_forever()
    send(sock, msg)
