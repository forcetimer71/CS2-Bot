import os
import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
import json
import threading
from flask import Flask

# Set up Flask app for keep-alive
app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run)
    t.daemon = True
    t.start()

# Create bot instance with minimal intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='CS!', intents=intents)

financial_message = None

# Load or create default data
def load_data():
    try:
        with open('nation_data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "nations": [{
                "name": "Varkhazia",
                "balance": 0,
                "income": 100,
                "added_time": datetime.now().timestamp()
            }]
        }

def save_data():
    global data
    with open('nation_data.json', 'w') as f:
        json.dump(data, f)

# Load initial data
data = load_data()

async def update_financial_message():
    global financial_message
    while True:
        try:
            # Only save the data to persist values
            save_data()

            if financial_message:
                now = datetime.now()
                nations_list = sorted(data.get("nations", [{"name": "Unknown", "income": 0, "balance": 0}]), key=lambda x: x.get("added_time", 0))
                content = f"Last Updated: {now.strftime('%d-%m-%Y')}\n\nNation - Income - Balance\n"
                for nation in nations_list:
                    content += f"**{nation['name']}** - ${nation['income']} - ${nation['balance']}\n"
                await financial_message.edit(content=content)

            # Update every hour instead of only once per day for more consistent activity
            await asyncio.sleep(3600)  # 1 hour
        except Exception as e:
            print(f"Error in update_financial_message: {e}")
            await asyncio.sleep(60)  # Wait a minute and try again if there's an error

@bot.event
async def on_ready():
    print(f'Bot is ready! Logged in as {bot.user}')
    bot.loop.create_task(update_financial_message())

@bot.command()
async def starttracking(ctx):
    global financial_message
    financial_message = await ctx.send("Initializing financial tracking...")
    now = datetime.now()
    nations_list = sorted(data.get("nations", []), key=lambda x: x.get("added_time", 0))
    content = f"Last Updated: {now.strftime('%d-%m-%Y')}\n\nNation - Income - Balance\n"
    for nation in nations_list:
        content += f"**{nation['name']}** - ${nation['income']} - ${nation['balance']}\n"
    await financial_message.edit(content=content)

@bot.command()
async def addnation(ctx, name: str, income: float = 0, balance: float = 0):
    global data
    data.setdefault("nations", [])
    data["nations"].append({
        "name": name,
        "income": income,
        "balance": balance,
        "added_time": datetime.now().timestamp()
    })
    save_data()
    await ctx.send(f"Added nation: {name} with income ${income} and balance ${balance}")

@bot.command()
async def setincome(ctx, name: str, amount: float):
    global data
    for nation in data.get("nations", []):
        if nation["name"].lower() == name.lower():
            nation["income"] = amount
            save_data()
            await ctx.send(f"Set income for {name} to ${amount}")
            return
    await ctx.send(f"Nation {name} not found")

@bot.command()
async def setbalance(ctx, name: str, amount: float):
    global data
    for nation in data.get("nations", []):
        if nation["name"].lower() == name.lower():
            nation["balance"] = amount
            save_data()
            await ctx.send(f"Set balance for {name} to ${amount}")
            return
    await ctx.send(f"Nation {name} not found")

@bot.command()
async def resetlist(ctx):
    global data
    data["nations"] = []
    save_data()
    await ctx.send("Nations list has been reset")

# Run the keep-alive web server
keep_alive()

# Get the Discord token from secrets
token = os.getenv('DISCORD_TOKEN')
if token:
    try:
        bot.run(token)
    except discord.errors.HTTPException as e:
        if e.status == 429:
            print("Rate limited. Restarting...")
            os.system("kill 1")  # Restarts the repl if rate limited
        else:
            raise e
else:
    print('DISCORD_TOKEN environment variable not found. Please set it and try again.')
