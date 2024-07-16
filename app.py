import os
from flask import Flask, render_template, request ,render_template_string
from flask_socketio import SocketIO, emit
from urllib.parse import urljoin
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

# Function to handle bot actions and emit corresponding images
def handle_bot_action(action):
    global bot_speaking

    # Set the bot speaking flag to True
    bot_speaking = True

    # Show the talking image initially
    image_url = images['talking']
    emit('update_image', image_url)  # Send the talking image URL to the client

    # Delay for transition effect
    time.sleep(0.5)

    # Determine the action and emit corresponding image and message
    if action == 'success':
        image_url = images['success']
        message = "Success message"
    elif action == 'loading':
        image_url = images['loading']
        message = "Loading message"
    elif action == 'sleeping':
        image_url = images['sleeping']
        message = "Sleeping message"
    elif action == 'failure':
        image_url = images['failure']
        message = "Failure message"
    else:
        image_url = images['default']
        message = "Default message"

    # Emit the image URL and message to the client
    emit('update_image', image_url)

    # Delay for transition effect
    time.sleep(0.5)
    emit('update_image', images['default'])

    # Set the bot speaking flag to False after finishing speaking
    bot_speaking = False

# Function to perform web search using various sources
def search_web(query):
    print(f"QUERY: {query}")

    # Define the search engines with their respective APIs or URLs
    search_engines = {
        "DuckDuckGo": "https://api.duckduckgo.com/",
        "Wikipedia": "https://en.wikipedia.org/w/api.php",
        "Jikan": f"https://api.jikan.moe/v4/anime?q={query}&limit=1"
    }
    
    results = {}  # Initialize results dictionary

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
        elif engine == "Jikan":
            try:
                response = requests.get(url)
                response.raise_for_status()
                anime_data = response.json()
                print(anime_data)
                # Extracting data from the Jikan API response
                if 'data' in anime_data and len(anime_data['data']) > 0:
                    anime = anime_data['data'][0]
                    abstract = anime.get("synopsis", "No information available")
                    results[engine] = {"abstract": abstract}
                else:
                    results[engine] = "No information available"
            except requests.exceptions.RequestException as e:
                results[engine] = f"Error: {e}"
            except KeyError as ke:
                results[engine] = f"Key Error: {ke}"
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
            except KeyError:
                pass
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

def search_video(query):
    search_url = f"https://www.googleapis.com/customsearch/v1?key={API_KEY}&cx={SEARCH_ENGINE_ID}&q={query}"
    print(f"Search URL: {search_url}")

    try:
        response = requests.get(search_url)
        response.raise_for_status()
        print("Search results fetched successfully")

        data = response.json()

        if 'items' in data:
            first_video = data['items'][0]  # Assuming you want the first video result
            video_url = first_video['link']
            print(f"Video URL: {video_url}")

            # Fetch HTML content of the video page
            video_page_response = requests.get(video_url)
            video_page_response.raise_for_status()
            print("Video page fetched successfully")

            video_page_soup = BeautifulSoup(video_page_response.content, 'html.parser')
            return video_page_soup.prettify()

        else:
            print("No video results found")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error searching for videos: {e}")
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
    
@app.route('/fetch_content')
def fetch_content():
    url = request.args.get('url')
    try:
        response = requests.get(url)
        response.raise_for_status()

        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')

        # Rewrite links to be absolute for proper rendering
        for link in soup.find_all('link'):
            if link.get('href') and not link.get('href').startswith('http'):
                link['href'] = urljoin(url, link['href'])

        # Rewrite image sources to be absolute
        for img in soup.find_all('img'):
            if img.get('src') and not img.get('src').startswith('http'):
                img['src'] = urljoin(url, img['src'])

        # Return rendered HTML content
        return render_template_string(str(soup))
    except requests.exceptions.RequestException as e:
        return f"Error fetching content: {e}", 500













# Socket event for handling user responses
@socketio.on('user_response')
def handle_user_response(user_input):
    global bot_speaking

    # Check if the bot is currently speaking
    if bot_speaking:
        return

    # Set the bot speaking flag to True
    bot_speaking = True

    # Emit the default image at the beginning of the response
    emit('update_image', images['default'])

    # Check if the user input matches the query pattern
    query_pattern = r'(?:tell me about|explain|what is|who is|where is|when is|why is|how is) (.+)'
    match = re.search(query_pattern, user_input.lower())

    if match:
        # Extract the query from the user input
        query = match.group(1).strip()

        # Search the web for the query
        search_results = search_web(query)
        image_results = search_image(query)
        video_results = search_video(query)

        # Emit search results and images to the client
        if image_results:
            emit('update_message', {'text': user_input, 'sender': 'user'})
            for image_url in image_results:
                emit('send_image', {'image': image_url, 'sender': 'bot'})

        # Emit video results to the client
        if video_results:
            emit('update_message', {'text': user_input, 'sender': 'user'})
            emit('send_video', {'video': video_results, 'sender': 'bot'})

        # Emit search results to the client
        for engine, result in search_results.items():
            text_message = f"{result['abstract']}"
            emit('update_message', {'text': user_input, 'sender': 'user'})
            emit('update_message', {'text': text_message, 'sender': 'bot'})

        # Use handle_bot_action to provide feedback based on user input
        handle_bot_action('success')  # You can change this action based on your logic

    elif "discord.gg" in user_input:
        # Handle Discord invite link
        emit('update_message', {'text': user_input, 'sender': 'user'})
        invite_code = user_input.split("/")[-1]
        response = requests.get(f"https://discord.com/api/v9/invites/{invite_code}?with_counts=true")
        server_info = response.json()
        server_name = server_info['guild']['name']
        server_image_url = f"https://cdn.discordapp.com/icons/{server_info['guild']['id']}/{server_info['guild']['icon']}.png"
        server_member_count = server_info['approximate_member_count']
        typing_image_url = images['talking']
        emit('update_image', typing_image_url)
        time.sleep(0.095 * len(greeting_message))
        emit('update_message', {'text': f"Server Name: {server_name}", 'sender': 'bot'})
        emit('update_message', {'text': f"Server Member Count: {server_member_count}", 'sender': 'bot'})
        emit('update_image', images['success'])
        time.sleep(1)
        emit('send_image', {'image': server_image_url, 'sender': 'bot'})

    else:
        # Handle default user input
        emit('update_message', {'text': user_input, 'sender': 'user'})
        handle_bot_action('default')  # Provide default feedback

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
