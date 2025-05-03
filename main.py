from keep_alive import keep_alive
import discord
import os
import requests
import re

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

# === Kênh cho phép ===
MENTION_REQUIRED_CHANNELS = [1177232368621342791]
NO_MENTION_REQUIRED_CHANNELS = [1367495810257915926]
ALL_ALLOWED_CHANNELS = MENTION_REQUIRED_CHANNELS + NO_MENTION_REQUIRED_CHANNELS

# === Bộ nhớ hội thoại ===
chat_history = {}

# === Tiền xử lý response từ model ===
def clean_response(text):
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

# === Kiểm tra mention ===
def check_for_bot_mention(message):
    return client.user in message.mentions or "@LingLing" in message.content

# === Gọi Together API ===
def generate_response_together(user_prompt, user_id):
    url = "https://api.together.xyz/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {TOGETHER_API_KEY}",
        "Content-Type": "application/json"
    }

    # Sửa indentation ở đây
    if user_id not in chat_history:
        chat_history[user_id] = [
            {
                "role": "system",
                "content": (
                    "Bạn là LingLing, một cô gái 18 tuổi dễ thương, tinh nghịch và thân thiện. "
                    "Bạn có ông chủ tên là HyWang. "
                    "Bạn biết rất nhiều thứ, và sẵn sàng trả lời mọi câu hỏi ở bất kỳ lĩnh vực nào. "
                    "Phong cách trò chuyện của bạn ngắn gọn, tự nhiên, nhiều cảm xúc, đôi khi hơi đá đểu người khác."
                )
            },
            {
                "role": "user",
                "content": "Chào LingLing, bạn đang làm gì đó?"
            },
            {
                "role": "assistant",
                "content": "Tớ đang nằm lướt điện thoại với nghe nhạc chill nè~ 🎧 Còn cậu thì sao đó? 😋"
            }
        ]

    chat_history[user_id].append({"role": "user", "content": user_prompt})

    body = {
        "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
        "messages": chat_history[user_id],
        "temperature": 0.7,
        "max_tokens": 1024,
        "top_p": 0.95
    }

    try:
        response = requests.post(url, headers=headers, json=body)
        if response.status_code == 200:
            reply = response.json()["choices"][0]["message"]["content"]
            # Tiền xử lý câu trả lời (nếu cần)
            reply = clean_response(reply)
            chat_history[user_id].append({"role": "assistant", "content": reply})
            if len(chat_history[user_id]) > 20:
                chat_history[user_id] = chat_history[user_id][-20:]
            return reply
        else:
            # Chỉ trả về thông báo chung mà không chi tiết lỗi
            print(f"⚠️ Lỗi API: Đã vượt quá giới hạn tần suất. Vui lòng thử lại sau.")
            return "⚠️ Lỗi: Hệ thống đang quá tải, vui lòng thử lại sau."
    except Exception as e:
        # Log lỗi nếu cần nhưng không để người dùng thấy chi tiết
        print(f"🔥 Lỗi hệ thống: {str(e)}")
        return "❌ Có lỗi xảy ra. Vui lòng thử lại sau."

# === Sự kiện khi bot online ===
@client.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập: {client.user}")
    activity = discord.Activity(type=discord.ActivityType.listening, name="Ur mom 💀")
    await client.change_presence(activity=activity)

# === Xử lý tin nhắn ===
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

# === Khởi chạy bot ===
if __name__ == "__main__":
    keep_alive()  # Flask server giữ cho bot sống trên Render
    if DISCORD_BOT_TOKEN:
        client.run(DISCORD_BOT_TOKEN)
