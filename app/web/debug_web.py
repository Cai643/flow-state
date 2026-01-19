import sys
import os

# Add current dir to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.Service.web_server import run_server

if __name__ == "__main__":
    print("Starting Web Server on 8080...")
    run_server(port=8080)
