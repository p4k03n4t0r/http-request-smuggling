FROM mitmproxy/mitmproxy
WORKDIR /app
COPY filter.py filter.py
ENTRYPOINT mitmdump --mode reverse:http://server:8000 -p 8002 -s filter.py --set block_global=false --no-http2