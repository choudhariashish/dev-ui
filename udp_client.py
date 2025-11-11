import socket
import json
import time
import random
import argparse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from socketserver import ThreadingMixIn

# Global variable to store the latest data
latest_data = {"status": "Waiting for data..."}
data_lock = threading.Lock()

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

class WebHandler(BaseHTTPRequestHandler):
    def modify_floating_values(self, data):
        """Recursively modify floating point values in the data structure."""
        if isinstance(data, dict):
            return {k: self.modify_floating_values(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.modify_floating_values(item) for item in data]
        elif isinstance(data, float):
            # Add a random value between -1 and 1 to the float
            return round(data + random.uniform(-1.0, 1.0), 2)
        return data

    def do_GET(self):
        if self.path == '/':
            try:
                with open('index.html', 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f'Error loading index.html: {str(e)}'.encode('utf-8'))
        elif self.path == '/data':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            with data_lock:
                # Create a deep copy of the data to avoid modifying the original
                import copy
                data_to_send = copy.deepcopy(latest_data)
                # Modify floating point values
                modified_data = self.modify_floating_values(data_to_send)
                self.wfile.write(json.dumps(modified_data, indent=2).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'404 Not Found')

def run_web_server(port=8000):
    server_address = ('', port)
    httpd = ThreadedHTTPServer(server_address, WebHandler)
    print(f"Web server started on http://localhost:{port}")
    httpd.serve_forever()

def main():
    global latest_data
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='UDP Client for receiving data from server')
    parser.add_argument('--ip', '--server-ip', dest='server_ip', 
                        default='127.0.0.1', 
                        help='UDP server IP address (default: 127.0.0.1)')
    parser.add_argument('--port', '--server-port', dest='server_port', 
                        type=int, default=5005, 
                        help='UDP server port (default: 5005)')
    parser.add_argument('--web-port', dest='web_port', 
                        type=int, default=8000, 
                        help='Web server port (default: 8000)')
    args = parser.parse_args()
    
    # Server configuration
    SERVER_IP = args.server_ip
    SERVER_PORT = args.server_port
    BUFFER_SIZE = 4096

    print(f"Configuration:")
    print(f"  UDP Server: {SERVER_IP}:{SERVER_PORT}")
    print(f"  Web Server: http://localhost:{args.web_port}")

    # Start web server in a separate thread
    web_thread = threading.Thread(target=run_web_server, args=(args.web_port,))
    web_thread.daemon = True
    web_thread.start()

    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1.0)
    
    # Set up server address
    server_address = (SERVER_IP, SERVER_PORT)
    print(f"Connecting to UDP server at {SERVER_IP}:{SERVER_PORT}")

    try:
        # Send initial message to register with server
        print("Sending registration...")
        sock.sendto(b"register", server_address)
        
        while True:
            try:
                # Receive data from the server
                data, addr = sock.recvfrom(BUFFER_SIZE)
                print(f"Received {len(data)} bytes from {addr}")
                
                # Parse the JSON data
                try:
                    json_str = data.decode('utf-8').strip()
                    print(f"Raw data: {json_str[:100]}...")  # Print first 100 chars of received data
                    
                    json_data = json.loads(json_str)
                    print("Successfully parsed JSON data")

                    # Update the latest data
                    with data_lock:
                        latest_data = json_data
                    
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Data updated")
                    
                except json.JSONDecodeError as je:
                    print(f"\n[!] JSON decode error: {je}")
                    print(f"Raw data that failed to decode: {data[:200]}")  # Print more of the raw data
                
            except socket.timeout:
                # Resend registration if we haven't heard back in a while
                print("No data received, resending registration...")
                sock.sendto(b"register", server_address)
                continue
                
            except KeyboardInterrupt:
                print("\nShutting down...")
                break
                
    except Exception as e:
        print(f"\n[!] Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        sock.close()
        print("\nConnection closed.")

if __name__ == "__main__":
    main()