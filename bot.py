import telebot
from telebot import types
import json
import os
import time
from flask import Flask
from threading import Thread
from supabase import create_client, Client

# --- 1. Web Hosting (Render መቆያ) ---
app = Flask('')
@app.route('/')
def home(): return "Fasil Lotto System is Active with Supabase! 🚀"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run); t.daemon = True; t.start()

# --- 2. ኮንፊገሬሽን (ከ Render Variables ያነባል) ---
TOKEN = os.environ.get("BOT_TOKEN")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Supabase መገናኛ
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

MY_ID = 8488592165          
ASSISTANT_ID = 7072611117   
GROUP_ID = -1003881429974
DB_CHANNEL_ID = -1003747262103
ADMIN_IDS = [MY_ID, ASSISTANT_ID]

PAYMENTS = {
    "me": {"tele": "0951381356", "cbe": "1000584461757"},
    "assistant": {"tele": "0973416038", "cbe": "1000718691323"}
}

# --- 3. ዳታቤዝ አያያዝ (Save & Restore) ---
data = {
    "users": {},
    "current_shift": "me",
    "boards": {
        "1": {"max": 25, "price": 50, "prize": "1ኛ 200, 2ኛ 100, 3ኛ 50", "active": True, "slots": {}},
        "2": {"max": 50, "price": 100, "prize": "1ኛ 400, 2ኛ 200, 3ኛ 100", "active": True, "slots": {}},
        "3": {"max": 100, "price": 200, "prize": "1ኛ 800, 2ኛ 400, 3ኛ 200", "active": True, "slots": {}}
    },
    "pinned_msgs": {"1": None, "2": None, "3": None}
}

def save_data():
    try:
        # ዳታውን ወደ Supabase መላክ
        supabase.table("game_data").upsert({"id": 1, "content": data}).execute()
        # ለተጨማሪ ጥንቃቄ ወደ ቻናል መላክ
        with open("backup.json", "w") as f: json.dump(data, f)
        with open("backup.json", "rb") as f:
            bot.send_document(DB_CHANNEL_ID, f, caption=f"🔄 DB Backup - {time.ctime()}")
    except Exception as e:
        print(f"❌ Save Error: {e}")

def load_data():
    global data
    try:
        # ዳታውን ከ Supabase መጫን
        response = supabase.table("game_data").select("content").eq("id", 1).execute()
        if response.data and len(response.data) > 0:
            db_content = response.data["content"]
            data.update(db_content)
            print("🔄 ዳታ ከ Supabase ተጭኗል (Restored)!")
            return True
    except Exception as e:
        print(f"❌ Restore Error: {e}")
    return False

# --- 4. የቦቱ ተግባራት (Functions) ---
def get_user(uid, name="ደንበኛ"):
    uid = str(uid)
    if uid not in data["users"]: data["users"][uid] = {"name": name, "wallet": 0}
    return data["users"][uid]

def main_menu_markup(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎮 ሰሌዳ ምረጥ", "👤 ፕሮፋይል", "🎫 የያዝኳቸው ቁጥሮች")
    if int(uid) in ADMIN_IDS: markup.add("⚙️ Admin Settings")
    return markup

def update_group_board(b_id):
    board = data["boards"][b_id]
    text = f"🎰 <b>ፋሲል ዕጣ - ሰሌዳ {b_id} (1-{board['max']})</b>\n🎫 መደብ፦ <b>{board['price']} ብር</b>\n━━━━━━━━━━━━━━━━━━━━━\n"
    line = ""
    for i in range(1, board["max"] + 1):
        s_i = str(i).zfill(2)
        if str(i) in board["slots"]:
            u_name = board["slots"][str(i)]; short = u_name[:5]
            line += f"<code>{s_i}</code>🔴{short}\t\t\t\t"
        else: line += f"<code>{s_i}</code>⬜️\t\t\t\t\t\t"
        if i % 2 == 0: text += line + "\n"; line = ""
    text += line + f"━━━━━━━━━━━━━━━━━━━━━\n🎁 <b>ሽልማት፦ {board['prize']}</b>\n🤖 @Fasil_assistant_bot"
    try:
        if data["pinned_msgs"].get(b_id):
            bot.edit_message_text(text, GROUP_ID, data["pinned_msgs"][b_id])
        else:
            m = bot.send_message(GROUP_ID, text)
            bot.pin_chat_message(GROUP_ID, m.message_id)
            data["pinned_msgs"][b_id] = m.message_id; save_data()
    except:
        m = bot.send_message(GROUP_ID, text)
        bot.pin_chat_message(GROUP_ID, m.message_id)
        data["pinned_msgs"][b_id] = m.message_id; save_data()

# --- 5. Message Handlers ---
@bot.message_handler(commands=['start'])
def welcome(message):
    uid = str(message.chat.id); user = get_user(uid, message.from_user.first_name)
    active_pay = PAYMENTS[data.get("current_shift", "me")]
    welcome_text = (f"👋 <b>እንኳን ወደ ፋሲል መዝናኛ መጡ!</b>\n👤 <b>ስም፦</b> {user['name']}\n💰 <b>ቀሪ፦</b> {user['wallet']} ብር\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n🏦 <b>Telebirr:</b> <code>{active_pay['tele']}</code>\n"
                    f"🔸 <b>CBE:</b> <code>{active_pay['cbe']}</code>")
    bot.send_message(uid, welcome_text, reply_markup=main_menu_markup(uid))

@bot.message_handler(func=lambda m: m.text == "🎮 ሰሌዳ ምረጥ")
def show_boards(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b_id, b_info in data["boards"].items():
        if b_info["active"]:
            markup.add(types.InlineKeyboardButton(f"🎰 ሰሌዳ {b_id} | 🎫 {b_info['price']} ብር", callback_data=f"select_{b_id}"))
    bot.send_message(message.chat.id, "<b>ለመጫወት የሚፈልጉትን ሰሌዳ ይምረጡ፦</b>", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    if call.data.startswith('select_'):
        bid = call.data.split('_'); user = get_user(call.message.chat.id)
        board = data["boards"][bid]
        if user["wallet"] < board["price"]:
            bot.answer_callback_query(call.id, "⚠️ በቂ ሂሳብ የሎትም!", show_alert=True); return
        markup = types.InlineKeyboardMarkup(row_width=5)
        btns = [types.InlineKeyboardButton(str(i), callback_data=f"pick_{bid}_{i}") for i in range(1, board["max"] + 1) if str(i) not in board["slots"]]
        markup.add(*btns)
        bot.edit_message_text(f"🎰 <b>ሰሌዳ {bid}</b>\nቁጥር ይምረጡ፦", call.message.chat.id, call.message.message_id, reply_markup=markup)
    elif call.data.startswith('pick_'):
        _, bid, num = call.data.split('_')
        uid = str(call.message.chat.id); user = get_user(uid)
        if user["wallet"] >= data["boards"][bid]["price"]:
            data["users"][uid]["wallet"] -= data["boards"][bid]["price"]
            data["boards"][bid]["slots"][num] = user["name"]
            save_data() # ቁጥር ሲመረጥ ወዲያው ሰርቨር ላይ ሴቭ ያደርጋል
            update_group_board(bid)
            bot.answer_callback_query(call.id, f"✅ ቁጥር {num} ተመርጧል!")
            bot.edit_message_text(f"✅ ተመዝግቧል! ቀሪ፦ {data['users'][uid]['wallet']} ብር", uid, call.message.message_id)

# --- ዋና ማስነሻ ---
if __name__ == "__main__":
    load_data() # ቦቱ ሲነሳ ዳታውን ከ Supabase ይጭናል
    keep_alive()
    bot.remove_webhook()
    while True:
        try: bot.polling(none_stop=True, interval=1, timeout=20)
        except: time.sleep(5)
