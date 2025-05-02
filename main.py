from flask import Flask
from threading import Thread
import discord
import os
import requests

# === Flask App (Keep Alive) ===
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# === ENV ===
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
if not TOGETHER_API_KEY:
    print("❌ Lỗi: Không tìm thấy TOGETHER_API_KEY!")

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not DISCORD_BOT_TOKEN:
    print("❌ Lỗi: Không tìm thấy DISCORD_BOT_TOKEN!")

# === Discord Intents ===
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# === Kênh ===
MENTION_REQUIRED_CHANNELS = [1177232368621342791]
NO_MENTION_REQUIRED_CHANNELS = [1367495810257915926]
ALL_ALLOWED_CHANNELS = MENTION_REQUIRED_CHANNELS + NO_MENTION_REQUIRED_CHANNELS

# === Bộ nhớ hội thoại ===
chat_history = {}

def check_for_bot_mention(message):
    return client.user in message.mentions or "@LingLing" in message.content

def generate_response_together(user_prompt, user_id):
    url = "https://api.together.xyz/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {TOGETHER_API_KEY}",
        "Content-Type": "application/json"
    }

    if user_id not in chat_history:
        chat_history[user_id] = [
            {"role": "system", "content": "Bạn là LingLing, cô gái 18 tuổi dễ thương..."},
            {"role": "user", "content": "Chào LingLing, bạn đang làm gì đó?"},
            {"role": "assistant", "content": "Tớ đang nằm nghe nhạc và ăn bánh nè 🍰 Còn cậu sao rồi?"}
        ]

    chat_history[user_id].append({"role": "user", "content": user_prompt})

    body = {
        "model": "meta-llama/Llama-3-8b-chat-hf",
        "messages": chat_history[user_id],
        "temperature": 0.7,
        "max_tokens": 1024,
        "top_p": 0.95
    }

    response = requests.post(url, headers=headers, json=body)
    if response.status_code == 200:
        reply = response.json()["choices"][0]["message"]["content"]
        chat_history[user_id].append({"role": "assistant", "content": reply})
        if len(chat_history[user_id]) > 20:
            chat_history[user_id] = chat_history[user_id][-20:]
        return reply
    else:
        return f"⚠️ Lỗi: {response.status_code} - {response.text}"

@client.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập: {client.user}")
    activity = discord.Activity(type=discord.ActivityType.listening, name="Ur mom 💀")
    await client.change_presence(activity=activity)

@client.event
async def on_message(message):
    if message.author == client.user or message.channel.id not in ALL_ALLOWED_CHANNELS:
        return

    if message.channel.id in MENTION_REQUIRED_CHANNELS and not check_for_bot_mention(message):
        return

    if message.author.bot and client.user not in message.mentions:
        return

    prompt = message.content.strip()
    if not prompt:
        await message.channel.send("❓ Vui lòng nhập nội dung!")
        return

    async with message.channel.typing():
        try:
            reply = generate_response_together(prompt, message.author.id)
            await message.channel.send(reply)
        except Exception as e:
            print(f"🔥 Lỗi khi gọi Together.ai: {str(e)}")
            await message.channel.send("❌ Có lỗi xảy ra: " + str(e))

# === Khởi chạy ===
if __name__ == "__main__":
    keep_alive()  # Mở web server để Render không tắt
    if DISCORD_BOT_TOKEN:
        client.run(DISCORD_BOT_TOKEN)
