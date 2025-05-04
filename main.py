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

# === Tìm kiếm thông tin CHÍNH XÁC ===
def search_structured_data(query):
    query = query.lower().strip()
    results = []
    
    # Tìm chính xác tiêu đề (không phân biệt hoa thường)
    for section in STRUCTURED_DATA:
        if query == section.lower():
            return f"=== {section} ===\n" + "\n".join(f"- {item}" for item in STRUCTURED_DATA[section])
    
    # Tìm trong nội dung (từ khóa có xuất hiện)
    for section, content in STRUCTURED_DATA.items():
        matched_items = [item for item in content if query in item.lower()]
        if matched_items:
            results.append(f"=== {section} ===")
            results.extend([f"- {item}" for item in matched_items])
    
    return "\n".join(results) if results else None

# === Xử lý prompt đặc biệt ===
def handle_special_queries(user_prompt):
    lower_prompt = user_prompt.lower()
    
    # Từ khóa đặc biệt cho từng loại dữ liệu
    triggers = {
        "rank": ["rank", "cấp bậc", "level"],
        "mine": ["mine", "đào mỏ", "zeta", "artifact"],
        "discord": ["discord", "server", "luật"]
    }
    
    # Kiểm tra loại dữ liệu được hỏi
    for data_type, keywords in triggers.items():
        if any(keyword in lower_prompt for keyword in keywords):
            query = re.sub("|".join(keywords), "", lower_prompt).strip()
            result = search_structured_data(query)
            if result:
                return result
            else:
                return f"Không tìm thấy thông tin về '{query}' trong {data_type.upper()}"
    
    # Yêu cầu thông tin tổng hợp
    if "toàn bộ thông tin" in lower_prompt or "tất cả thông tin" in lower_prompt:
        full_info = []
        for section, content in STRUCTURED_DATA.items():
            full_info.append(f"=== {section} ===")
            full_info.extend([f"- {item}" for item in content])
        return "\n".join(full_info)
    
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
                    "Bạn là LingLing, 18 tuổi, thích đá đểu"
                    "Ông chủ của bạn tên là HyWang."
                    "Trò chuyện theo kiểu giang hồ"
                    "Khi được hỏi về dữ liệu từ file:\n"
                    "1. Chỉ trả lời đúng thông tin được yêu cầu\n"
                    "2. Rank: Trả lời từ RankWiki.txt\n"
                    "3. Mine: Trả lời từ Mine.txt\n"
                    "4. Discord: Trả lời từ InfoDiscord.txt\n"
                    "5. Nếu không hỏi về thông tin trong file mẫu thì trả lời bình thường không cần theo định dạng"
                    "6. Không được trả lời tất cả 3 file cùng 1 lúc"
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
        "model": "meta-llama/Llama-3-70b-chat-hf",
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
            print(f"⚠️ Lỗi API: {response.status_code}")
            return "⚠️ Hệ thống đang quá tải!"
    except Exception as e:
        print(f"🔥 Lỗi hệ thống: {str(e)}")
        return "❌ Có lỗi xảy ra!"

# === Sự kiện Discord ===
@client.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập: {client.user}")
    activity = discord.Activity(type=discord.ActivityType.listening, name="HyWang 💖")
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
            if len(reply) > 2000:
                for chunk in [reply[i:i+2000] for i in range(0, len(reply), 2000)]:
                    await message.channel.send(chunk)
            else:
                await message.channel.send(reply)
        except Exception as e:
            print(f"🔥 Lỗi khi xử lý tin nhắn: {str(e)}")
            await message.channel.send("❌ Bot bị lỗi, thử lại sau!")

# === Khởi chạy ===
if __name__ == "__main__":
    keep_alive()
    if DISCORD_BOT_TOKEN:
        client.run(DISCORD_BOT_TOKEN)
