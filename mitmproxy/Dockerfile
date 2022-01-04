FROM mitmproxy/mitmproxy:6.0.2
WORKDIR /app
COPY filter.py filter.py
ENTRYPOINT mitmdump --mode reverse:http://${SERVER_HOSTNAME}:${SERVER_PORT} -p 8002 -s filter.py --set block_global=false --no-http2