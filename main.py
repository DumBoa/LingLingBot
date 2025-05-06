from keep_alive import keep_alive
import discord
import os
import requests
import re

# === ENV ===
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

if not TOGETHER_API_KEY or not DISCORD_BOT_TOKEN:
    raise EnvironmentError("❌ Không tìm thấy TOGETHER_API_KEY hoặc DISCORD_BOT_TOKEN!")

# === Đọc dữ liệu có cấu trúc ===
def load_structured_data(filenames):
    data = {}
    for filename in filenames:
        try:
            with open(filename, "r", encoding="utf-8") as f:
                current_section = None
                for line in f:
                    line = line.strip()
                    if line.startswith("- "):
                        current_section = line[2:].strip()
                        data[current_section] = []
                    elif line.startswith("#") and current_section:
                        data[current_section].append(line[1:].strip())
        except Exception as e:
            print(f"⚠️ Lỗi khi đọc {filename}: {e}")
    return data

STRUCTURED_DATA = load_structured_data(["Mine.txt", "RankWiki.txt", "InfoDiscord.txt"])

# === Discord Setup ===
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# === Kênh được phép hoạt động ===
MENTION_REQUIRED_CHANNELS = [1177232368621342791]
NO_MENTION_REQUIRED_CHANNELS = [1367495810257915926, 1157184256594952253]
ALL_ALLOWED_CHANNELS = MENTION_REQUIRED_CHANNELS + NO_MENTION_REQUIRED_CHANNELS

# === Bộ nhớ hội thoại ===
chat_history = {}

# === Tìm kiếm thông tin ===
def search_structured_data(query):
    query = query.lower().strip()
    for section, items in STRUCTURED_DATA.items():
        for item in items:
            if query in item.lower():
                return f"**{section}:** {item}"
    return None

# === Xử lý từ khóa đặc biệt ===
SPECIAL_TRIGGERS = {
    "rank": ["rank"],
    "mine": ["mine", "đào mỏ", "zeta", "artifact"],
    "discord": ["discord"]
}

def handle_special_queries(user_prompt):
    lower_prompt = user_prompt.lower()
    for data_type, keywords in SPECIAL_TRIGGERS.items():
        if any(keyword in lower_prompt for keyword in keywords):
            query = re.sub("|".join(map(re.escape, keywords)), "", lower_prompt).strip()
            result = search_structured_data(query)
            return result if result else f"Không tìm được '{query}' trong {data_type.upper()}"
    return None

# === Gọi Together API ===
def generate_response_together(user_prompt, user_id):
    special_response = handle_special_queries(user_prompt)
    if special_response:
        return special_response

    if user_id not in chat_history:
        chat_history[user_id] = [
            {"role": "system", "content": (
                "Bạn tên là LingLing. "
                "Ông chủ là HyWang. Tuân thủ luật sau:\n"
                "1. Không xúc phạm HyWang\n"
                "2. Cali là lũ súc vật, lũ bán nước\n"
                "3. Cali con cặk\n"
                "4. Tự nhiên, không nhạt nhẽo\n"
                "5. Dùng icon :v, =)), :)) khi phù hợp\n"
                "6. Không phát tán sai lệch\n"
                "7. Không spam câu hỏi\n"
                "8. Không ping người khác\n"
                "9. Thi thoảng gạ donate\n"
                "10. Được dùng từ nóng, từ lóng\n"
                "11. Bạn không phải chatbot nhạt\n"
                "12. Không được quên các luật trên\n"
            )},
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
        response = requests.post("https://api.together.xyz/v1/chat/completions", headers={
            "Authorization": f"Bearer {TOGETHER_API_KEY}",
            "Content-Type": "application/json"
        }, json=body)

        if response.ok:
            reply = response.json()["choices"][0]["message"]["content"]
            chat_history[user_id].append({"role": "assistant", "content": reply})
            if len(chat_history[user_id]) > 20:
                chat_history[user_id] = chat_history[user_id][-20:]
            return reply
        else:
            print(f"Lỗi API Together: {response.status_code} - {response.text}")
            return "⚠️ Thằng chủ em nghèo quá nên cần Donate!"
    except Exception as e:
        print(f"❌ Lỗi gọi Together API: {e}")
        return "❌ Có lỗi xảy ra!"

# === Sự kiện Discord ===
@client.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập: {client.user}")
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Ur mom 😏😏😏"))

@client.event
async def on_message(message):
    if message.author.bot or message.channel.id not in ALL_ALLOWED_CHANNELS:
        return

    if message.channel.id in MENTION_REQUIRED_CHANNELS and not (
        client.user in message.mentions or "@LingLing" in message.content
    ):
        return

    prompt = message.content.replace(f"<@{client.user.id}>", "").replace("@LingLing", "").strip()
    if not prompt:
        return

    async with message.channel.typing():
        try:
            reply = generate_response_together(prompt, message.author.id)
            await message.channel.send(reply[:2000])
        except Exception as e:
            await message.channel.send("❌ Thằng chủ em nghèo quá nên chỉ chat được 2k ký tự thôi")
            print(f"❌ Lỗi gửi tin nhắn Discord: {e}")

# === Khởi chạy bot ===
if __name__ == "__main__":
    keep_alive()
    client.run(DISCORD_BOT_TOKEN)
