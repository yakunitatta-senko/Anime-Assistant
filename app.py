from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from bs4 import BeautifulSoup
import requests
import socket
import time
import re

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")  # All origins are allowed for demonstration purposes

# Image URLs
images = {
    'talking': 'https://i.pinimg.com/564x/35/9c/d0/359cd058a28ae764614941e0a87e0a63.jpg',
    'success': 'https://i.pinimg.com/736x/b0/a9/f1/b0a9f1c9519766d39105633d18bca3a4.jpg',
    'loading': 'https://i.pinimg.com/236x/ce/51/f7/ce51f7cd1021598d668e58673107debf.jpg',
    'sleeping': 'https://i.pinimg.com/236x/25/1a/cc/251acccd8874a4a32b476c5ec1e422e9.jpg',
    'failure': 'https://i.pinimg.com/236x/31/f5/9f/31f59fbd772a407359ad9f6d22c85103.jpg',
    'default': 'https://i.pinimg.com/236x/47/eb/f8/47ebf82f44698d88f8bccc5c5a3edb50.jpg'
}

# Greeting message
greeting_message = "Well, hello there! Fancy meeting you here."

# Flag to track whether the bot is speaking
bot_speaking = False


# Function to perform web search using various sources
def search_web(query):
    print(f"QUERY: {query}")

    # Define the search engines with their respective APIs or URLs
    search_engines = {
        "DuckDuckGo": "https://api.duckduckgo.com/",
        "Wikipedia": "https://en.wikipedia.org/w/api.php"
    }
    results = {}

    for engine, url in search_engines.items():
        if engine == "DuckDuckGo":
            # Fetch data from DuckDuckGo's API
            params = {"q": query, "format": "json"}
            try:
                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                abstract = data.get("Abstract", "No information available")
                results[engine] = {"abstract": abstract}
            except requests.exceptions.RequestException as e:
                results[engine] = f"Error: {e}"
        else:
            # Fetch data from Wikipedia API
            params = {
                "action": "query",
                "format": "json",
                "prop": "extracts|pageimages",
                "exintro": True,
                "explaintext": True,
                "titles": query,
                "piprop": "original"
            }
            try:
                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                pages = data["query"]["pages"]
                page_id = next(iter(pages))
                extract = pages[page_id]["extract"] or "..."
                results[engine] = {"abstract": extract}
            except requests.exceptions.RequestException as e:
                results[engine] = f"Error: {e}"

    return results


# Define your Google Custom Search API key and search engine ID
API_KEY = 'AIzaSyBNCNpIH26nsO_umj1LHMSMCo1jzmgkuaI'
SEARCH_ENGINE_ID = 'a1d15feaa6af94024'

def search_image(query):
    search_url = f"https://www.googleapis.com/customsearch/v1?key={API_KEY}&cx={SEARCH_ENGINE_ID}&searchType=image&q={query}"

    try:
        response = requests.get(search_url)
        response.raise_for_status()
        data = response.json()
        
        # Extract image URLs from the search results
        image_urls = [item['link'] for item in data.get('items', [])]
        
        return image_urls
    except requests.exceptions.RequestException as e:
        print(f"Error searching for images: {e}")
        return None

# Define context processor to pass images variable to templates
@app.context_processor
def inject_images():
    return dict(images=images)


# Define routes
@app.route('/')
def home():
    # Show the talking image initially
    image_url = images['talking']
    return render_template('index.html', image_url=image_url)


# Socket event for sending greeting message
@socketio.on('send_message')
def send_message():
    global bot_speaking

    # Check if the bot is already speaking
    if bot_speaking:
        return

    # Set the bot speaking flag to True
    bot_speaking = True

    # Show the talking image initially
    image_url = images['talking']
    emit('update_image', image_url)  # Send the talking image URL to the client

    # Emit the greeting message as a whole
    emit('update_message', {'text': greeting_message, 'sender': 'bot'})

    # Wait for typing animation duration
    time.sleep(0.015 * len(greeting_message))

    # Change the image to default after finishing typing
    image_url = images['default']
    emit('update_image', image_url)

    # Emit the typing_finished event
    emit('typing_finished')

    # Set the bot speaking flag to False after finishing speaking
    bot_speaking = False


# Socket event for handling user responses
@socketio.on('user_response')
def handle_user_response(user_input):
    global bot_speaking

    # Check if the bot is currently speaking
    if bot_speaking:
        return

    # Set the bot speaking flag to True
    bot_speaking = True

    # Check if the user input matches the query pattern
    query_pattern = r'(?:tell me about|explain|what is|who is|where is|when is|why is|how is) (.+)'
    match = re.search(query_pattern, user_input.lower())

    if match:
        # Extract the query from the user input
        query = match.group(1).strip()

        # Search the web for the query
        search_results = search_web(query)
        image_results = search_image(query)

        # Emit search results to the client
        for engine, result in search_results.items():
            text_message = f"{engine.upper()}: {result['abstract']}"
            emit('update_message', {'text': text_message, 'sender': 'bot'})
        if image_results:
            for image_url in image_results:
                emit('send_image', {'image': image_url, 'sender': 'bot'})

    # Check if the user input is a Discord invite link
    elif "discord.gg" in user_input:
        emit('update_message', {'text': user_input, 'sender': 'user'})

        # Extract the invite code from the link
        invite_code = user_input.split("/")[-1]

        # Make a request to retrieve information about the Discord server
        response = requests.get(f"https://discord.com/api/v9/invites/{invite_code}?with_counts=true")
        server_info = response.json()

        # Extract relevant information
        server_name = server_info['guild']['name']
        server_image_url = f"https://cdn.discordapp.com/icons/{server_info['guild']['id']}/{server_info['guild']['icon']}.png"
        server_member_count = server_info['approximate_member_count']

        # Show the typing image
        typing_image_url = images['talking']
        emit('update_image', typing_image_url)
        time.sleep(0.095 * len(greeting_message))

        # Emit the server information to the client
        emit('update_message', {'text': f"Server Name: {server_name}", 'sender': 'bot'})
        emit('update_message', {'text': f"Server Member Count: {server_member_count}", 'sender': 'bot'})
        emit('update_image', images['success'])
        time.sleep(1)

        # Emit the server image URL
        emit('send_image', {'image': server_image_url, 'sender': 'bot'})

    else:
        # Display the user's input as a hyperlink
        emit('update_message', {'text': user_input, 'sender': 'user'})

    # Set the bot speaking flag to False after finishing speaking
    bot_speaking = False


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
    socketio.run(app, port=port, debug=True)
