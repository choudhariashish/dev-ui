import socket
import json
import time
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
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            # Simple HTML page with auto-refresh
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>UDP Data Viewer</title>
                <style>
                    body { 
                        font-family: Arial, sans-serif; 
                        max-width: 1200px; 
                        margin: 0 auto; 
                        padding: 20px;
                        background-color: #f5f5f5;
                    }
                    .container {
                        background: white;
                        padding: 20px;
                        border-radius: 8px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }
                    pre {
                        background: #f8f9fa;
                        padding: 15px;
                        border-radius: 4px;
                        overflow-x: auto;
                        white-space: pre-wrap;
                        word-wrap: break-word;
                    }
                    .header {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        margin-bottom: 20px;
                    }
                    .last-updated {
                        color: #666;
                        font-size: 0.9em;
                    }
                </style>
                <meta http-equiv="refresh" content="1">
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>UDP Data Viewer</h1>
                        <div class="last-updated" id="last-updated">Last updated: Never</div>
                    </div>
                    <pre id="json-data">Loading data...</pre>
                </div>
                <script>
                    // Format JSON with syntax highlighting
                    function syntaxHighlight(json) {
                        if (typeof json != 'string') {
                            json = JSON.stringify(json, undefined, 2);
                        }
                        json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                        return json.replace(
                            /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
                            function (match) {
                                let cls = 'number';
                                if (/^"/.test(match)) {
                                    if (/:$/.test(match)) {
                                        cls = 'key';
                                    } else {
                                        cls = 'string';
                                    }
                                } else if (/true|false/.test(match)) {
                                    cls = 'boolean';
                                } else if (/null/.test(match)) {
                                    cls = 'null';
                                }
                                return '<span class="' + cls + '">' + match + '</span>';
                            }
                        );
                    }

                    // Update the display with new data
                    function updateData() {
                        fetch('/data')
                            .then(response => response.json())
                            .then(data => {
                                document.getElementById('json-data').innerHTML = syntaxHighlight(data);
                                document.getElementById('last-updated').textContent = 
                                    'Last updated: ' + new Date().toLocaleTimeString();
                            })
                            .catch(error => {
                                console.error('Error fetching data:', error);
                            });
                    }

                    // Initial load
                    updateData();
                    
                    // Update every second
                    setInterval(updateData, 1000);
                </script>
            </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))
            
        elif self.path == '/data':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            with data_lock:
                self.wfile.write(json.dumps(latest_data, indent=2).encode('utf-8'))
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
    
    # Server configuration
    SERVER_IP = '127.0.0.1'
    SERVER_PORT = 5005
    BUFFER_SIZE = 4096

    # Start web server in a separate thread
    web_thread = threading.Thread(target=run_web_server)
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