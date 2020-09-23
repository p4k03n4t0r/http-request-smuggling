# http-request-smuggling-demo

Simple demo of http request smuggling. There are two examples:

- TE-CL: Mitmproxy (TE) -> Gunicorn (CL)
- CL-TE: HAProxy (CL) -> Gunicorn (TE)

To try it out spin up the environment using docker-compose. Use the clients in the demo-clients folder to get a working example of request smuggling.
