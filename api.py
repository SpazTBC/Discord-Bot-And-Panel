import os
from flask import Flask, render_template, request, jsonify
import json
import requests

app = Flask(__name__)

# Path to files containing user data
ADMINS_FILE = 'admins.txt'
OWNERS_FILE = 'owner.txt'
USERS_FILE = 'users.txt'

# Function to read user IDs from a file and return them as a list of tuples (ID, username)
def read_user_ids_from_file(filename):
    with open(filename, 'r') as file:
        return [tuple(line.strip().split(',')) for line in file]


# Function to write a list of user IDs to a file
def write_user_ids_to_file(user_ids, filename):
    with open(filename, 'a') as file:
        # Read existing user IDs from the file
        existing_ids = set()
        try:
            with open(filename, 'r') as f:
                for line in f:
                    user_id, _ = line.strip().split(',', 1)
                    if user_id:
                        existing_ids.add(user_id)
        except FileNotFoundError:
            pass
        
        # Write only new user IDs to the file
        for user_id in user_ids:
            if str(user_id) not in existing_ids:
                file.write(str(user_id) + '\n')
                existing_ids.add(str(user_id))



# Function to read user IDs and usernames from a file and return them as a list of tuples
def read_user_data_from_file(filename):
    with open(filename, 'r') as file:
        return [tuple(line.strip().split(',')) if ',' in line else (line.strip(), None) for line in file]


# Function to write a list of user IDs and usernames to a file
def write_user_data_to_file(user_data, filename):
    with open(filename, 'w') as file:
        for user_id, username in user_data:
            file.write(f"{user_id},{username}\n")

# Function to fetch username from ID
def fetch_username(user_id):
    # Logic to fetch username from user_id, replace with your implementation
    return f"User {user_id}"

@app.route('/')
def index():
    # Get the username from the request
    username = request.args.get('username', 'Guest')

    # Read user IDs and usernames from files
    admins = read_user_data_from_file(ADMINS_FILE)
    owners = read_user_ids_from_file(OWNERS_FILE)  # Read only IDs for owners
    users = read_user_data_from_file(USERS_FILE)

    # Pass the admin, owner, and user data to the template
    return render_template('homepage.html', admins=admins, owners=owners, users=users, username=username)


################# SECURITY FUNCTIONALITY #################

authenticated_user_ids = ['680620023600906342', '9876543210']  # List of authenticated user IDs
approved_ids = []  # List of approved user IDs


@app.route('/discord/adminpanel/verify', methods=['GET', 'POST'])
def verify_admin_panel_access():
    if request.method == 'POST':
        # Check if the X-Discord-ID header is present in the request
        if 'X-Discord-ID' in request.headers:
            user_discord_id = request.headers.get('X-Discord-ID')
            if user_discord_id in authenticated_user_ids:
                # Add the user Discord ID to the list of approved IDs
                approved_ids.append(user_discord_id)
                return jsonify({'message': 'Authentication successful', 'user_discord_id': user_discord_id}), 200
            else:
                # Authentication failed due to user not being in the list of authenticated IDs
                print("Authentication failed for user Discord ID:", user_discord_id)
                return jsonify({'message': 'Authentication failed. You are not authorized to access the admin panel.'}), 401
        else:
            # X-Discord-ID header not found in the POST request
            print("X-Discord-ID header not found in POST request")
            return jsonify({'message': 'X-Discord-ID header not found'}), 400
    elif request.method == 'GET':
        # For GET requests, return the list of approved user IDs
        return jsonify({'approved_ids': approved_ids}), 200





@app.route('/adminpanel')
def indext():
    # Get the username from the request
    username = request.args.get('username', 'Guest')

    # Read user IDs and usernames from files
    admins = read_user_data_from_file(ADMINS_FILE)
    owners = read_user_ids_from_file(OWNERS_FILE)  # Read only IDs for owners
    users = read_user_data_from_file(USERS_FILE)

    # Pass the admin, owner, and user data to the template
    return render_template('dashboard.html', admins=admins, owners=owners, users=users, username=username)

################# ADMIN PANEL AND OTHER FUNCTIONALITIES ABOVE #################
@app.route('/update', methods=['POST'])
def update_data():
    # Get JSON data from the request
    data = request.json

    # Update data based on received JSON
    admins = data.get('admins', [])
    owners = data.get('owners', [])
    users = data.get('users', [])

    # Write updated data to files
    write_user_ids_to_file(admins, ADMINS_FILE)
    write_user_ids_to_file(owners, OWNERS_FILE)
    write_user_data_to_file(users, USERS_FILE)

    return 'Data updated successfully.'


######################### DISCORD FUNCTIONALITY #########################
admins = []
kicked_users = []
banned_users = []

# Path to the shared data store JSON file
DATA_FILE = 'shared_data.json'

def load_data():
    try:
        with open(DATA_FILE, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        # If the file doesn't exist or is empty, return an empty data structure
        return {'banned_users': [], 'kicked_users': [], 'admins': [], 'role_assignments': []}


# Function to save data to the shared data store
def save_data(data):
    with open(DATA_FILE, 'w') as file:
        json.dump(data, file, indent=4)

# Route to handle ban requests
@app.route('/userupdate/ban/<user_id>', methods=['POST'])
def ban_user(user_id):
    reason = request.json.get('reason', 'Panel Ban')
    data = load_data()
    data['banned_users'].append({'user_id': user_id, 'reason': reason})
    save_data(data)
    send_data_to_bot(data)  # Send updated data to the bot
    return jsonify({'message': f'User with ID {user_id} has been banned. Reason: {reason}'}), 200

# Route to handle kick requests
@app.route('/userupdate/kick/<user_id>', methods=['POST'])
def kick_user(user_id):
    reason = request.json.get('reason', 'Panel Kick')
    data = load_data()
    data['kicked_users'].append({'user_id': user_id, 'reason': reason})
    save_data(data)
    send_data_to_bot(data)  # Send updated data to the bot
    return jsonify({'message': f'User with ID {user_id} has been kicked. Reason: {reason}'}), 200


# Route to handle admin additions
@app.route('/userupdate/addadmin/<user_id>', methods=['POST'])
def add_admin(user_id):
    username = request.json.get('username')
    if user_id and username:
        data = load_data()
        data['admins'].append({'user_id': user_id, 'username': username, 'action': 'add'})  # Include action field
        save_data(data)
        # Write to admins file
        with open('admins.txt', 'a') as file:
            file.write(f"{user_id},{username}\n")
        send_data_to_bot(data)  # Send updated data to the bot
        return jsonify({'message': f'User with ID {user_id} has been added as an admin. Username: {username}'}), 200
    else:
        return jsonify({'error': 'Both user ID and username must be provided'}), 400

# Route to handle admin removals
@app.route('/userupdate/removeadmin/<user_id>', methods=['POST'])
def remove_admin(user_id):
    username = None
    with open("admins.txt", "r+") as file:
        lines = file.readlines()
        file.seek(0)
        for line in lines:
            if not line.startswith(f"{user_id},"):
                file.write(line)
            else:
                username = line.split(',')[1].strip()
        file.truncate()

    if username:
        data = load_data()
        data['admins'].append({'user_id': user_id, 'username': username, 'action': 'remove'})
        save_data(data)
        send_data_to_bot(data)
        return jsonify({'message': f'Admin with ID {user_id} has been removed from admins.txt.'}), 200
    else:
        return jsonify({'error': f'Admin with ID {user_id} not found in admins.txt.'}), 404




@app.route('/userupdate/data', methods=['GET', 'POST'])
def handle_data():
    if request.method == 'GET':
        data = load_data()
        return jsonify(data), 200
    elif request.method == 'POST':
        new_data = request.json
        current_data = load_data()
        current_data.update(new_data)  # Merge the new data with the current data
        save_data(current_data)
        send_data_to_bot(current_data)  # Send updated data to the bot
        return jsonify({'message': 'Data updated successfully'}), 200
    else:
        return jsonify({'error': 'Unsupported request method'}), 405


# Function to send updated data to the bot
def send_data_to_bot(data):
    # Example of how to process the data in the bot
    print("Received updated data:", data)
    # Further logic to inform the bot about the updated data


############################## GET REQUESTS ##############################
@app.route('/userupdate/banned', methods=['GET'])
def get_banned_users():
    user_id = request.args.get('user_id')  # Get the user ID from the query parameters
    if user_id:
        # Filter banned users based on user ID
        return jsonify([user for user in banned_users if user['user_id'] == user_id]), 200
    else:
        # Return all banned users if no user ID is provided
        return jsonify(banned_users), 200

@app.route('/userupdate/kicked', methods=['GET'])
def get_kicked_users():
    user_id = request.args.get('user_id')  # Get the user ID from the query parameters
    if user_id:
        # Filter kicked users based on user ID
        return jsonify([user for user in kicked_users if user['user_id'] == user_id]), 200
    else:
        # Return all kicked users if no user ID is provided
        return jsonify(kicked_users), 200

@app.route('/userupdate/admins', methods=['GET'])
def get_admins():
    user_id = request.args.get('user_id')  # Get the user ID from the query parameters
    if user_id:
        # Filter admins based on user ID
        return jsonify([user for user in admins if user['user_id'] == user_id]), 200
    else:
        # Return all admins if no user ID is provided
        return jsonify(admins), 200



# Define the route for retrieving Discord guild owner information
@app.route('/discord/discordinfo', methods=['POST', 'GET'])
def discord_info():
    if request.method == 'POST':
        try:
            # Receive guild information from the bot
            data = request.json
            # Check if the discinfo.json file exists
            if os.path.isfile('discinfo.json'):
                # Read existing data from discinfo.json
                with open('discinfo.json', 'r') as file:
                    existing_data = file.readlines()
                    existing_guilds = [json.loads(line) for line in existing_data]
                # Check if the received data is different from existing data
                if data.get('discord_name') and data.get('guild_id') and data not in existing_guilds:
                    # Write received data to discinfo.json
                    with open('discinfo.json', 'a') as file:
                        file.write(json.dumps(data) + '\n')
                    return jsonify({'message': 'Guild information received and saved successfully.'}), 200
                else:
                    return jsonify({'message': 'Received guild information is the same as existing data. No update needed.'}), 200
            else:
                # Write received data to discinfo.json as it's the first time receiving data
                with open('discinfo.json', 'w') as file:
                    json.dump(data, file)
                return jsonify({'message': 'Guild information received and saved successfully.'}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    elif request.method == 'GET':
        try:
            # Check if discinfo.json exists
            if os.path.isfile('discinfo.json'):
                # Read guild information from discinfo.json
                with open('discinfo.json', 'r') as file:
                    data = file.readlines()
                    # Extracting all guild information
                    guilds_data = [json.loads(line) for line in data]
                # Return the information as JSON response
                return jsonify(guilds_data), 200
            else:
                return jsonify({'error': 'Guild information file not found.'}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
