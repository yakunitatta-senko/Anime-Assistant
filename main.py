import socket

# Define the HTML content for different pages
main_page = """
<!DOCTYPE html>
<html>
<head>
    <title>Assistant Bot</title>
    <style>
        /* Define your CSS styles here */
        body {
            font-family: Arial, sans-serif;
        }
        /* Add more styles as needed */
    </style>
</head>
<body>
    <h1>Welcome to Assistant Bot</h1>
    <!-- Add more content as needed -->
    <img src="/default_image">
</body>
</html>
"""

# Define image paths
image_paths = {
    "/talking_image": "path/to/talking_image.jpg",
    "/success_image": "path/to/success_image.jpg",
    "/loading_image": "path/to/loading_image.jpg",
    "/sleeping_image": "path/to/sleeping_image.jpg",
    "/failure_image": "path/to/failure_image.jpg",
    "/default_image": "path/to/default_image.jpg"
}

def serve_image(path):
    """Serve image content"""
    try:
        with open(image_paths[path], 'rb') as f:
            return f.read()
    except FileNotFoundError:
        return b"Not Found"

def handle_request(request):
    """Handle client requests"""
    parts = request.split()
    if len(parts) > 1 and parts[0] == "GET":
        if parts[1] in image_paths:
            return serve_image(parts[1])
        elif parts[1] == "/":
            return main_page.encode()
    return b"Not Found"

def run_server():
    """Run the web server"""
    host = '127.0.0.1'
    port = 8080

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((host, port))
        server_socket.listen(1)
        print(f"Server listening on {host}:{port}")

        while True:
            client_socket, client_address = server_socket.accept()
            with client_socket:
                request = client_socket.recv(1024).decode()
                response = handle_request(request)
                client_socket.sendall(response)

if __name__ == "__main__":
    run_server()
