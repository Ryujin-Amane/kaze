from flask import Flask
from threading import Thread
import logging

# Disable Flask startup logging for cleaner console
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask("")

@app.route('/')
def home():
    return "I am alive!"

def run():
    # Run on port 8080 (Render expects web services to bind to a port, often 10000 or dynamically assigned via PORT env var)
    # 0.0.0.0 is crucial for Docker/Render access
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
