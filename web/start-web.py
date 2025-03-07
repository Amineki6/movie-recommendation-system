import http.server
import socketserver
import webbrowser
import os

WEB_DIR = os.path.abspath("web")  
PORT = 5500  # Default port


# Define HTTP handler
Handler = http.server.SimpleHTTPRequestHandler

# Start the server
with socketserver.TCPServer(("localhost", PORT), Handler) as httpd:
    print(f"Serving at http://localhost:{PORT}")

    # Open the login.html file inside the auth/ directory
    webbrowser.open(f"http://localhost:{PORT}/auth/login.html")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.shutdown()
