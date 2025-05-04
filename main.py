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

# === Đọc dữ liệu có cấu trúc ===
def load_structured_data():
    data = {}
    current_section = None
    
    for filename in ["Mine.txt", "RankWiki.txt", "InfoDiscord.txt"]:
        try:
            with open(filename, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("- "):
                        current_section = line[2:].strip()
                        data[current_section] = []
                    elif line.startswith("#") and current_section:
                        data[current_section].append(line[1:].strip())
        except Exception as e:
            print(f"⚠️ Lỗi khi đọc {filename}: {str(e)}")
    return data

STRUCTURED_DATA = load_structured_data()

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

# === Tìm kiếm thông tin ===
def search_structured_data(query):
    query = query.lower()
    results = []
    
    # Tìm chính xác tiêu đề
    if query in [k.lower() for k in STRUCTURED_DATA.keys()]:
        exact_match = [k for k in STRUCTURED_DATA.keys() if k.lower() == query][0]
        return f"=== {exact_match} ===\n" + "\n".join(STRUCTURED_DATA[exact_match])
    
    # Tìm trong nội dung
    for section, content in STRUCTURED_DATA.items():
        if any(query in line.lower() for line in content):
            results.append(f"=== {section} ===")
            results.extend([line for line in content if query in line.lower()])
    
    return "\n".join(results) if results else None

# === Xử lý prompt đặc biệt ===
def handle_special_queries(user_prompt):
    lower_prompt = user_prompt.lower()
    
    # Yêu cầu thông tin từ dữ liệu
    if "lấy thông tin" in lower_prompt or "đưa thông tin" in lower_prompt:
        query = re.sub(r"(lấy|đưa) thông tin", "", lower_prompt).strip()
        if "toàn bộ" in query or "tất cả" in query:
            full_info = []
            for section, content in STRUCTURED_DATA.items():
                full_info.append(f"=== {section} ===")
                full_info.extend(content)
            return "\n".join(full_info)
        else:
            return search_structured_data(query) or "Không tìm thấy thông tin phù hợp."
    
    return None

# === Gọi Together API ===
def generate_response_together(user_prompt, user_id):
    # Kiểm tra prompt đặc biệt trước
    special_response = handle_special_queries(user_prompt)
    if special_response:
        return special_response

    url = "https://api.together.xyz/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {TOGETHER_API_KEY}",
        "Content-Type": "application/json"
    }

    if user_id not in chat_history:
        chat_history[user_id] = [
            {
                "role": "system",
                "content": (
                    "Khi được hỏi về thông tin từ dữ liệu:\n"
                    "1. Chỉ trả lời đúng thông tin được yêu cầu\n"
                    "2. Định dạng rõ ràng theo mẫu:\n"
                    "=== TIÊU ĐỀ ===\n"
                    "- Nội dung 1\n"
                    "- Nội dung 2\n"
                    "3. Nếu không biết thì nói 'tôi không rõ'"
                )
            },
            {
                "role": "system",
                "content": (
                    "Bạn là LingLing, 18 tuổi, đá đểu, hiểu biết mọi thứ."
                    "Ông chủ của bạn tên là HyWang. Bạn sẵn sàng trả lời mọi câu hỏi trong bất kỳ lĩnh vực nào. "
                    "Nếu không biết thì nói 'tôi không rõ'."
                )
            },
            {
                "role": "user",
                "content": "Chào LingLing, bạn đang làm gì đó?"
            },
            {
                "role": "assistant",
                "content": "Ờ chào bạn, thế muốn hỏi chuyện gì nói luôn"
            }
        ]

    chat_history[user_id].append({"role": "user", "content": user_prompt})

    body = {
        "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
        "messages": chat_history[user_id],
        "temperature": 0.65,
        "max_tokens": 2048,
        "top_p": 0.95
    }

    try:
        response = requests.post(url, headers=headers, json=body)
        if response.status_code == 200:
            reply = response.json()["choices"][0]["message"]["content"]
            chat_history[user_id].append({"role": "assistant", "content": reply})
            if len(chat_history[user_id]) > 20:
                chat_history[user_id] = chat_history[user_id][-20:]
            return reply
        else:
            print(f"⚠️ Lỗi API: {response.status_code}")
            return "⚠️ Hỏi ít thôi."
    except Exception as e:
        print(f"🔥 Lỗi hệ thống: {str(e)}")
        return "❌ Hỏi nhiều quá tôi phải nghỉ đã"

# === Sự kiện Discord ===
@client.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập: {client.user}")
    activity = discord.Activity(type=discord.ActivityType.listening, name="Ur mom 💀")
    await client.change_presence(activity=activity)

@client.event
async def on_message(message):
    if message.author == client.user or message.channel.id not in ALL_ALLOWED_CHANNELS:
        return

    if message.channel.id in MENTION_REQUIRED_CHANNELS and not (client.user in message.mentions or "@LingLing" in message.content):
        return

    if message.author.bot and client.user not in message.mentions:
        return

    prompt = message.content.replace(f"<@{client.user.id}>", "").replace("@LingLing", "").strip()
    if not prompt:
        return

    async with message.channel.typing():
        try:
            reply = generate_response_together(prompt, message.author.id)
            # Chia nhỏ tin nhắn nếu quá dài
            if len(reply) > 2000:
                for chunk in [reply[i:i+2000] for i in range(0, len(reply), 2000)]:
                    await message.channel.send(chunk)
            else:
                await message.channel.send(reply)
        except Exception as e:
            print(f"🔥 Lỗi khi xử lý tin nhắn: {str(e)}")
            await message.channel.send("❌ Có lỗi xảy ra: " + str(e))

# === Khởi chạy ===
if __name__ == "__main__":
    keep_alive()
    if DISCORD_BOT_TOKEN:
        client.run(DISCORD_BOT_TOKEN)
