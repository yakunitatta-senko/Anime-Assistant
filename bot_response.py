from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import time
import socket
import sys

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# Greeting message
greeting_message = "Well, hello there! Fancy meeting you here."

# Define routes
@app.route('/')
def home():
    return render_template('index.html')

# Socket event for sending greeting message
@socketio.on('send_message')
def send_message():
    for char in greeting_message:
        emit('update_message', char)
        time.sleep(0.2)  # Adjust speed of typing animation

if __name__ == '__main__':
    # Find an available port dynamically
    port = 5000
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(('localhost', port))
            s.close()
            break
        except socket.error as e:
            port += 1

    print(f"Server is running on port {port}")
    socketio.run(app, port=port)