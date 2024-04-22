import discord
from discord.ext import commands
import requests
from dotenv import load_dotenv
import os
import asyncio
import json

# Load environment variables
load_dotenv()

# Get the token from environment variables
TOKEN = os.getenv('DISCORD_TOKEN')

# API endpoint URL
API_URL = "http://localhost:5000/update"
UPDATES_URL = "http://localhost:5000/userupdate"
APIVERIFY_URL = 'http://localhost:5000'

# Initialize lists for admin and owner IDs
ADMIN_IDS = []
OWNER_ID = []

# Create bot instance with intents
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='-', intents=intents)

# Load admin IDs from admins.txt when bot starts up
def load_admin_ids():
    try:
        with open('admins.txt', 'r') as file:
            for line in file:
                admin_id = int(line.strip().split(',')[0])  # Extract only the ID part
                ADMIN_IDS.append(admin_id)
    except FileNotFoundError:
        print("admins.txt not found. Initializing ADMIN_IDS as an empty list.")

# Load owner IDs from owner.txt when bot starts up
def load_owner_ids():
    try:
        with open('owner.txt', 'r') as file:
            for line in file:
                owner_id = int(line.strip().split(',')[0])  # Extract only the ID part
                OWNER_ID.append(owner_id)
    except FileNotFoundError:
        print("owner.txt not found. Initializing OWNER_ID as an empty list.")

# Check if the author of the message is an admin
def is_admin(ctx):
    return ctx.author.id in ADMIN_IDS

# Check if the author of the message is an owner
def is_owner(ctx):
    return ctx.author.id in OWNER_ID




# Function to get user IDs from the guild
def get_user_ids(guild):
    return [member.id for member in guild.members]

# Function to get user IDs and usernames from the guild
def get_user_data(guild):
    return [(member.id, member.name) for member in guild.members]

async def send_update_request(guild_id):
    last_sent_admins = set()
    last_sent_owners = set()

    while True:
        guild = bot.get_guild(guild_id)
        if guild is None:
            print(f"Guild with ID {guild_id} not found.")
            return

        # Get current owner and admin IDs
        current_admins = set(ADMIN_IDS)
        current_owners = set(OWNER_ID)

        # Check if owner or admin IDs have changed
        if current_admins != last_sent_admins or current_owners != last_sent_owners:
            data = {
                "admins": list(current_admins),
                "owners": list(current_owners),
                "users": get_user_data(guild)
            }

            try:
                response = requests.post(API_URL, json=data)
                if response.status_code == 200:
                    pass #print("Data sent to API successfully!")
                    # Update last sent IDs
                    last_sent_admins = current_admins
                    last_sent_owners = current_owners
                else:
                    print(f"Failed to send data to API. Status code: {response.status_code}")
            except Exception as e:
                print(f"An error occurred while sending data to API: {e}")

        await asyncio.sleep(60)  # Adjust the interval as needed



# Command to clear messages
@bot.command(name="clear", aliases=["cl"], brief="Clear a certain amount of messages")
@commands.check(lambda ctx: is_owner(ctx) or is_admin(ctx))
async def clear(ctx, amount: int = 25):
    await ctx.channel.purge(limit=amount)

# Command to list all users in the guild
@bot.command(name='list_users')
async def list_users(ctx):
    guild = ctx.guild
    members = guild.members
    user_list = ', '.join([member.name for member in members])
    await ctx.send(f'All users: {user_list}')

# Command to add an admin
@bot.command(name='addadmin')
@commands.check(is_owner)
async def add_admin(ctx, member: discord.Member):
    try:
        with open('admins.txt', 'a') as file:
            file.write(f"{member.id},{member.name}\n")
        ADMIN_IDS.append(member.id)
        await ctx.send(f'{member.name} has been added as an admin.')
    except Exception as e:
        await ctx.send(f'An error occurred: {e}')

# Command to kick a user
@bot.command(name='kick', pass_context=True)
@commands.has_permissions(kick_members=True)
@commands.check(is_admin)
async def kick_user(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f'Kicked {member.name} from the server. Reason: {reason}')

# Command to get the ID of a user
@bot.command(name='get_user_id')
@commands.check(is_admin)
async def get_user_id(ctx, member: discord.Member):
    await ctx.send(f"The user's ID is: {member.id}")

# Command to add the invoker as an admin
@bot.command(name='AdminMe')
async def admin_me(ctx):
    if ctx.author.id == OWNER_ID:
        await ctx.send("Sorry, you're already the owner.")
        return
    
    if ctx.author.id in ADMIN_IDS:
        await ctx.send("You're already an admin.")
        return
    
    try:
        with open('admins.txt', 'a') as file:
            file.write(f"{ctx.author.id},{ctx.author.name}\n")
        ADMIN_IDS.append(ctx.author.id)
        await ctx.send("You've been added as an admin.")
    except Exception as e:
        await ctx.send(f'An error occurred: {e}')

# Command to manually send update request
@bot.command(name="update")
@commands.check(lambda ctx: is_owner(ctx) or is_admin(ctx))
async def update(ctx):
    for guild in bot.guilds:
        await send_update_request(guild.id)  # Send update request for each guild


# Function to fix the format of admins.txt and owner.txt
async def fix_format(ctx):
    # Initialize lists to store corrected data
    admins_data = []
    owner_data = []

    # Fetch all members from the guild
    guild = ctx.guild
    members = guild.members

    # Get IDs and usernames of all members
    users_data = [(member.id, member.name) for member in members]

    # Read data from admins.txt and owner.txt
    with open('admins.txt', 'r') as file:
        for line in file:
            admin_id = int(line.strip().split(',')[0])
            username = get_username(admin_id, users_data)
            admins_data.append((admin_id, username))

    with open('owner.txt', 'r') as file:
        for line in file:
            owner_id = int(line.strip().split(',')[0])
            username = get_username(owner_id, users_data)
            owner_data.append((owner_id, username))

    # Write corrected data back to files
    write_data_to_file(admins_data, 'admins.txt')
    write_data_to_file(owner_data, 'owner.txt')

    await ctx.send("Format fixed successfully!")

# Function to get username from ID
def get_username(user_id, users_data):
    for uid, username in users_data:
        if uid == user_id:
            return username
    return "Unknown"

# Function to write data to file
def write_data_to_file(data, filename):
    with open(filename, 'w') as file:
        for user_id, username in data:
            file.write(f"{user_id},{username}\n")

# Command to fix the format of admins.txt and owner.txt
@bot.command(name='fixformat', aliases=['fix'])
async def fix_format_command(ctx):
    await fix_format(ctx)



@bot.command(name='resetdata', aliases=['reset'])
async def reset_data_command(ctx):
    try:
        data = {'banned_users': [], 'kicked_users': [], 'admins': []}
        response = requests.post("http://localhost:5000/userupdate/data", json=data)
        if response.status_code == 200:
            await ctx.send("Data reset successfully.")
        else:
            await ctx.send(f"Failed to reset data. Response status code: {response.status_code}")
    except Exception as e:
        await ctx.send(f"An error occurred while resetting data: {e}")


@bot.command(name='authenticate', aliases=['auth'])
async def authenticate_command(ctx):
    try:
        # Get the Discord user ID
        user_discord_id = str(ctx.author.id)

        # Construct the URL for the POST request to add the user's ID
        post_url = "http://localhost:5000/discord/adminpanel/verify"

        # Send the POST request to add the user's ID to the approved_ids list
        post_headers = {'X-Discord-ID': user_discord_id}
        post_response = requests.post(post_url, headers=post_headers)

        # Check if the POST request was successful
        if post_response.status_code == 200:
            # Now send the GET request to check if the user's ID is approved
            get_url = "http://localhost:5000/discord/adminpanel/verify"
            get_response = requests.get(get_url)

            # Check if the GET request was successful
            if get_response.status_code == 200:
                approved_ids = get_response.json().get('approved_ids', [])
                if user_discord_id in approved_ids:
                    # User is approved, send the authentication message
                    await ctx.author.send("Authentication successful. Click the link to access the admin panel: " + post_url)
                    await ctx.send("Check your private messages for the authentication link.")
                else:
                    # User is not approved
                    await ctx.author.send("You are not authorized to access the admin panel.")
            else:
                # GET request failed
                await ctx.author.send(f"GET request failed. Response status code: {get_response.status_code}")

        else:
            # POST request failed, extract error message from API response
            error_message = post_response.json().get('message')
            await ctx.author.send(f"{error_message}")

    except Exception as e:
        await ctx.author.send(f"An error occurred while authenticating: {e}")






################## FIXING FILES BEFORE THE COMMAND IS ISSUED ##################

# Function to fix the format of admins.txt and owner.txt
async def update_files(guild):
    # Initialize lists to store corrected data
    admins_data = []
    owner_data = []

    # Fetch all members from the guild
    members = guild.members

    # Get IDs and usernames of all members
    users_data = [(member.id, member.name) for member in members]

    # Read data from admins.txt and owner.txt
    with open('admins.txt', 'r') as file:
        for line in file:
            admin_id = int(line.strip().split(',')[0])
            username = get_username(admin_id, users_data)
            admins_data.append((admin_id, username))

    with open('owner.txt', 'r') as file:
        for line in file:
            owner_id = int(line.strip().split(',')[0])
            username = get_username(owner_id, users_data)
            owner_data.append((owner_id, username))


    # Write corrected data back to files
    write_data_to_file(admins_data, 'admins.txt')
    write_data_to_file(owner_data, 'owner.txt')


def print_file_contents(filename):
    with open(filename, 'r') as file:
        contents = file.read()
        print(contents)



# Function to write data to file
def write_data(data, filename):
    print(f"Writing data to {filename}:")
    for entry in data:
        print(f"Entry: {entry[0]}, {entry[1]}")
    with open(filename, 'w') as file:
        for entry in data:
            file.write(f"{entry[0]},{entry[1]}\n")
    print(f"Data written to {filename} successfully.")




################### API HANDLING BELOW ###################
async def handle_api_requests(guild):
    while True:
        try:
            # Get data from the /userupdate/data endpoint
            data_url = f"{UPDATES_URL}/data"
            response = requests.get(data_url)
            if response.status_code == 200:
                data = response.json()

                # Process banned users
                for ban_data in data.get('banned_users', []):
                    user_id = ban_data['user_id']
                    reason = ban_data.get('reason', 'Panel Ban')
                    # Ban the user
                    await ban_user(guild, user_id, reason)
                    # Remove processed banned user from the data
                    data['banned_users'] = [ban for ban in data['banned_users'] if ban['user_id'] != user_id]

                # Process kicked users
                for kick_data in data.get('kicked_users', []):
                    user_id = kick_data['user_id']
                    reason = kick_data.get('reason', 'Panel Kick')
                    # Kick the user
                    await kick_user(guild, user_id, reason)
                    # Remove processed kicked user from the data
                    data['kicked_users'] = [kick for kick in data['kicked_users'] if kick['user_id'] != user_id]

                # Process new admins
                for admin_data in data.get('admins', []):
                    user_id = admin_data['user_id']
                    username = admin_data['username']
                    action = admin_data.get('action', 'unknown')  # Get the action
                    # Send message to the specified channel
                    channel_id = 1231011666251219006  # Change to your desired channel ID
                    channel = guild.get_channel(channel_id)
                    if channel:
                        if action == 'add':
                            await channel.send(f"{username} has been added as an admin.")
                        elif action == 'remove':
                            await channel.send(f"{username} has been removed as an admin.")
                        else:
                            await channel.send(f"Unknown action for admin {username}.")
                    # Remove processed new admin request from the data
                    data['admins'] = [admin for admin in data['admins'] if admin['user_id'] != user_id]

                # Process role assignments
                for role_data in data.get('role_assignments', []):
                    user_id = role_data['user_id']
                    role_id = role_data['role_id']
                    # Find the member object by user ID
                    member = discord.utils.get(guild.members, id=int(user_id))
                    if member:
                        # Find the role object by role ID
                        role = discord.utils.get(guild.roles, id=int(role_id))
                        if role:
                            # Assign the role to the member
                            await member.add_roles(role)
                            print(f"Assigned role '{role.name}' to user '{member.name}'.")
                        else:
                            print(f"Role with ID '{role_id}' not found.")
                    else:
                        print(f"Member with ID '{user_id}' not found.")
                    # Remove processed role assignment from the data
                    data['role_assignments'] = [role for role in data['role_assignments'] if role['user_id'] != user_id]

                # Send the updated data back to the API
                response = requests.post(data_url, json=data)
                if response.status_code == 200:
                    # Commented out the following line
                    # print("Updated data sent back to API successfully.")
                    pass
                else:
                    print("Failed to send updated data back to API.")
        except Exception as e:
            print(f"An error occurred while handling API requests: {e}")
        await asyncio.sleep(20)  # Adjust the interval as needed


async def kick_user(guild, user_id, reason):
    try:
        member = await guild.fetch_member(user_id)
        await member.kick(reason=reason)
        print(f"User {user_id} has been kicked from the server.")
        await asyncio.sleep(1)  # Introduce a delay of 1 second
        # Debugging: Print the data being sent to the API
        new_data =  {'banned_users': [], 'kicked_users': [], 'admins': []}
        print("Data being sent to API:", new_data)
        # Send the new data to the API
        # await reset_data()  # Remove the reset_data() call
    except discord.NotFound:
        print(f"User {user_id} not found in the server.")
    except discord.Forbidden:
        print("Bot does not have permission to kick users.")
    except discord.HTTPException as e:
        print(f"Failed to kick user {user_id}: {e}")

async def ban_user(guild, user_id, reason):
    try:
        member = await guild.fetch_member(user_id)
        await guild.ban(member, reason=reason)
        print(f"User {user_id} has been banned from the server.")
        await asyncio.sleep(1)  # Introduce a delay of 1 second
        # Debugging: Print the data being sent to the API
        new_data =  {'banned_users': [], 'kicked_users': [], 'admins': []}
        print("Data being sent to API:", new_data)
        # Send the new data to the API
        # await reset_data()  # Remove the reset_data() call
    except discord.NotFound:
        print(f"User {user_id} not found in the server.")
    except discord.Forbidden:
        print("Bot does not have permission to ban users.")
    except discord.HTTPException as e:
        print(f"Failed to ban user {user_id}: {e}")


async def send_guild_info_to_api(bot):
    while True:
        try:
            # Get the guild
            guild = bot.guilds[0]
            # Fetch the owner's member object
            owner = await guild.fetch_member(guild.owner_id)

            # Get all roles in the guild except @everyone
            roles_info = {}
            for role in guild.roles:
                if role.name != '@everyone':
                    roles_info[str(role.id)] = role.name

            guild_info = {
                'guild_id': guild.id,
                'guild_owner': str(owner),
                'discord_name': guild.name,  # Getting the guild's name
                'roles': roles_info  # Include roles information
            }

            response = requests.post("http://localhost:5000/discord/discordinfo", json=guild_info)
            if response.status_code == 200:
                pass  # Guild information sent to API successfully.
            else:
                print(f"Failed to send guild information to API. Response status code: {response.status_code}")
                print(f"Response content: {response.content}")
        except Exception as e:
            print(f"An error occurred while sending guild information to API: {e}")

        # Wait for 24 hours before the next refresh
        await asyncio.sleep(10)  # Check again in 24 hours.




async def update_on_ready():
    await bot.wait_until_ready()
    for guild in bot.guilds:
        await update_files(guild)
        bot.loop.create_task(send_update_request(guild.id))
        bot.loop.create_task(handle_api_requests(guild))

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    bot.loop.create_task(update_on_ready())
    await send_guild_info_to_api(bot)

load_admin_ids()
load_owner_ids()
# Run the bot
bot.run(TOKEN)
