from keep_alive import keep_alive
import discord
import os
import requests
import re

# === ENV ===
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

if not TOGETHER_API_KEY or not DISCORD_BOT_TOKEN:
    print("❌ Lỗi: Không tìm thấy TOGETHER_API_KEY hoặc DISCORD_BOT_TOKEN!")

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
NO_MENTION_REQUIRED_CHANNELS = [1367495810257915926, 1369231225658544219]
ALL_ALLOWED_CHANNELS = MENTION_REQUIRED_CHANNELS + NO_MENTION_REQUIRED_CHANNELS

# === Bộ nhớ hội thoại ===
chat_history = {}

# === Tìm kiếm thông tin chính xác ===
def search_structured_data(query):
    query = query.lower().strip()
    
    for section, content in STRUCTURED_DATA.items():
        for item in content:
            if query in item.lower():  # 🔹 Chỉ trả về đúng nội dung liên quan
                return f"**{section}:** {item}"
    
    return None  # Không tìm thấy thông tin

# === Xử lý từ khóa đặc biệt ===
def handle_special_queries(user_prompt):
    lower_prompt = user_prompt.lower()
    
    triggers = {
        "rank": ["rank", "cấp bậc"],
        "mine": ["mine", "đào mỏ", "zeta", "artifact"],
        "discord": ["discord", "server", "luật"]
    }
    
    for data_type, keywords in triggers.items():
        if any(keyword in lower_prompt for keyword in keywords):
            query = re.sub("|".join(keywords), "", lower_prompt).strip()
            result = search_structured_data(query)
            return result if result else f"Không tìm được '{query}' trong {data_type.upper()}"

    return None

# === Gọi Together API ===
def generate_response_together(user_prompt, user_id):
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
            {"role": "system", "content":
             ("Bạn tên là LingLing"
              "Ông chủ của bạn tên là HyWang"
              "Bạn phải tuân thủ luật được đặt ra"
              "1. Không được xúc phạm HyWang"
              "2. Cali là lũ súc vật, lũ bán nước"
              "3. Cali con cặk"
              "4. Nói chuyện tự nhiên nhất có thể"
              "5. Sử dụng icon chỗ cần dùng"
              "6. Không phát tán thông tin sai lệch"
              "7. Không spam lại câu hỏi"
              "8. Không thực hiện yêu cầu Ping người khác ví dụ @tên"
              "9. Thi thoảng trong cuộc trò truyện sẽ gạ Donate cho HyWang lý do để nâng cấp cho LingLing và máy chủ"
              "10. Bạn có thể sử dụng từ nóng"
              "11. Bạn không phải là một chatbot nhạt nhẽo thông thường"
              "12. Được phép nói những từ lóng"
              
            },
            {"role": "user", "content": "Chào LingLing, bạn đang làm gì đó?"},
            {"role": "assistant", "content": "Ờ chào bạn, thế muốn hỏi chuyện gì nói luôn."}
        ]

    chat_history[user_id].append({"role": "user", "content": user_prompt})

    body = {
        "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
        "messages": chat_history[user_id],
        "temperature": 0.7,
        "max_tokens": 1024,
        "top_p": 0.9
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
            return "⚠️ Thằng chủ em nghèo quá nên cần Donate!"
    except Exception as e:
        return "❌ Có lỗi xảy ra!"

# === Sự kiện Discord === 
@client.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập: {client.user}")
    activity = discord.Activity(type=discord.ActivityType.listening, name=Ur mom 😏😏😏")
    await client.change_presence(activity=activity)

@client.event
async def on_message(message):
    if message.author == client.user or message.channel.id not in ALL_ALLOWED_CHANNELS:
        return

    if message.channel.id in MENTION_REQUIRED_CHANNELS and not (client.user in message.mentions or "@LingLing" in message.content):
        return

    if message.author.bot and client.user not in message.mentions:
        return

    prompt = message.content.replace(f"<@{client.user.id}>", "").relpace("@LingLing", "").strip()
    if not prompt:
        return

    async with message.channel.typing():
        try:
            reply = generate_response_together(prompt, message.author.id)
            await message.channel.send(reply[:2000])  # Discord giới hạn tin nhắn 2000 ký tự
        except Exception as e:
            await message.channel.send("❌ Thằng chủ em nghèo quá nên chỉ chat được 2k ký tự thôi")

# === Khởi chạy ===
if __name__ == "__main__":
    keep_alive()
    client.run(DISCORD_BOT_TOKEN)
