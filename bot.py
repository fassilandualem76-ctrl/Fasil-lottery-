import telebot
from telebot import types
import json
import os
from flask import Flask
from threading import Thread
import time
import requests
from pymongo import MongoClient

# --- 1. Web Hosting ---
app = Flask('')
@app.route('/')
def home(): return "Fasil Lotto System is LIVE! 🔥"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- 2. ቦት መረጃዎች & MongoDB ---
TOKEN = "8721334129:AAHuEJDpuZf5vZ0GzKGPfRALlG3cA1TUmF0"
# የአንተን MongoDB URL እዚህ ጋር አስገባ
MONGO_URL = "mongodb+srv://fassilandualem76_db_user:68yAgMwYuR232BvN@lottery.jigg9z4.mongodb.net/?appName=Lottery"

client = MongoClient(MONGO_URL)
db = client['fasil_bingo_db']
collection = db['game_data']

MY_ID = 8488592165          
ASSISTANT_ID = 7072611117   
GROUP_ID = -1003881429974
ADMIN_IDS = [MY_ID, ASSISTANT_ID]

PAYMENTS = {
    "me": {"tele": "0951381356", "cbe": "1000584461757"},
    "assistant": {"tele": "0973416038", "cbe": "1000718691323"}
}

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# --- 3. ዳታቤዝ አያያዝ (MongoDB) ---
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
        collection.update_one({"_id": "master_data"}, {"$set": {"content": data}}, upsert=True)
    except: pass

def load_data():
    global data
    try:
        record = collection.find_one({"_id": "master_data"})
        if record: data.update(record["content"])
    except: pass

# --- 4. የሰሌዳ ዲዛይን (Fixed Error 400) ---
def update_group_board(b_id):
    board = data["boards"][b_id]
    text = f"🎰 <b>ፋሲል ዕጣ - ሰሌዳ {b_id} (1-{board['max']})</b>\n"
    text += f"🎫 መደብ፦ <b>{board['price']} ብር</b>\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━\n"
    line = ""
    for i in range(1, board["max"] + 1):
        s_i = str(i).zfill(2)
        if str(i) in board["slots"]:
            u_name = board["slots"][str(i)]
            short = u_name[:5]
            line += f"<code>{s_i}</code>🔴{short}\t\t"
        else:
            line += f"<code>{s_i}</code>⬜️\t\t\t\t"
        if i % 2 == 0:
            text += line + "\n"
            line = ""
    text += line + f"\n━━━━━━━━━━━━━━━━━━━━━\n🎁 <b>ሽልማት፦ {board['prize']}</b>\n🤖 ለመጫወት፦ @Fasil_assistant_bot"

    # ማስተካከያ፦ ሁልጊዜ ኪቦርድ መጨመር (ይህ ስህተቱን ይፈታል)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎮 አሁኑኑ ተጫወት", url="https://t.me/Fasil_assistant_bot"))

    try:
        if data["pinned_msgs"].get(b_id):
            bot.edit_message_text(text, GROUP_ID, data["pinned_msgs"][b_id], reply_markup=markup)
        else:
            m = bot.send_message(GROUP_ID, text, reply_markup=markup)
            bot.pin_chat_message(GROUP_ID, m.message_id)
            data["pinned_msgs"][b_id] = m.message_id
            save_data()
    except:
        m = bot.send_message(GROUP_ID, text, reply_markup=markup)
        bot.pin_chat_message(GROUP_ID, m.message_id)
        data["pinned_msgs"][b_id] = m.message_id
        save_data()

# --- 5. ዋና ዋና ትዕዛዞች ---
@bot.message_handler(commands=['start'])
def welcome(message):
    uid = str(message.chat.id)
    if uid not in data["users"]:
        data["users"][uid] = {"name": message.from_user.first_name, "wallet": 0}
        save_data()
    user = data["users"][uid]
    active_pay = PAYMENTS[data.get("current_shift", "me")]
    
    welcome_text = (f"👋 <b>እንኳን ወደ ፋሲል መዝናኛ መጡ!</b>\n\n👤 <b>ስም፦</b> {user['name']}\n💰 <b>ቀሪ፦</b> {user['wallet']} ብር\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n🏦 <b>Telebirr:</b> <code>{active_pay['tele']}</code>\n"
                    f"🔸 <b>CBE:</b> <code>{active_pay['cbe']}</code>")
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎮 ሰሌዳ ምረጥ", "👤 ፕሮፋይል", "🎫 የያዝኳቸው ቁጥሮች")
    if int(uid) in ADMIN_IDS: markup.add("⚙️ Admin Settings")
    bot.send_message(uid, welcome_text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🎮 ሰሌዳ ምረጥ")
def show_boards(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for b_id, b_info in data["boards"].items():
        if b_info["active"]:
            markup.add(types.InlineKeyboardButton(f"🎰 ሰሌዳ {b_id} | 🎫 {b_info['price']} ብር", callback_data=f"select_{b_id}"))
    bot.send_message(message.chat.id, "<b>ሰሌዳ ይምረጡ፦</b>", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    uid = str(call.message.chat.id)
    is_admin = call.from_user.id in ADMIN_IDS

    if call.data.startswith('select_'):
        bid = call.data.split('_')
        user = data["users"][uid]
        board = data["boards"][bid]
        if user["wallet"] < board["price"]:
            bot.answer_callback_query(call.id, "⚠️ በቂ ሂሳብ የሎትም!", show_alert=True); return
        markup = types.InlineKeyboardMarkup(row_width=5)
        btns = [types.InlineKeyboardButton(str(i), callback_data=f"pick_{bid}_{i}") for i in range(1, board["max"] + 1) if str(i) not in board["slots"]]
        markup.add(*btns)
        bot.edit_message_text(f"🎰 <b>ሰሌዳ {bid}</b>\nቁጥር ይምረጡ፦", uid, call.message.message_id, reply_markup=markup)

    elif call.data.startswith('pick_'):
        _, bid, num = call.data.split('_')
        if data["users"][uid]["wallet"] >= data["boards"][bid]["price"]:
            data["users"][uid]["wallet"] -= data["boards"][bid]["price"]
            data["boards"][bid]["slots"][num] = data["users"][uid]["name"]
            save_data(); update_group_board(bid)
            bot.answer_callback_query(call.id, f"✅ ቁጥር {num} ተመርጧል!")
            bot.edit_message_text(f"✅ ተመዝግቧል! ቀሪ ሂሳብ፦ {data['users'][uid]['wallet']} ብር", uid, call.message.message_id)
        else: bot.answer_callback_query(call.id, "⚠️ በቂ ሂሳብ የሎትም!")

    elif call.data.startswith('approve_') and is_admin:
        target = call.data.split('_')
        m = bot.send_message(call.from_user.id, f"💵 ለ ID {target} የሚጨመረውን ብር ይጻፉ፦")
        bot.register_next_step_handler(m, finalize_app, target)

def finalize_app(message, target):
    try:
        amt = int(message.text)
        data["users"][str(target)]["wallet"] += amt
        save_data()
        bot.send_message(target, f"✅ <b>{amt} ብር ተጨምሯል!</b>\nበሰሌዳ ላይ የሚወጣውን ስምዎን ይጻፉ፦")
        bot.register_next_step_handler_by_chat_id(target, save_name, target)
    except: bot.send_message(message.chat.id, "❌ ቁጥር ብቻ ይጻፉ።")

def save_name(message, uid):
    data["users"][str(uid)]["name"] = message.text[:5]
    save_data()
    bot.send_message(uid, f"✅ ስምዎ ተመዝግቧል!")

@bot.message_handler(content_types=['photo', 'text'])
def handle_receipts(message):
    if message.chat.type != 'private' or message.text in ["🎮 ሰሌዳ ምረጥ", "👤 ፕሮፋይል", "🎫 የያዝኳቸው ቁጥሮች"]: return
    uid = str(message.chat.id)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ አፅድቅ", callback_data=f"approve_{uid}"))
    cap = f"📩 <b>አዲስ ደረሰኝ</b>\n👤 <b>ከ፦</b> {message.from_user.first_name}\n🆔 <code>{uid}</code>"
    for adm in ADMIN_IDS:
        if message.photo: bot.send_photo(adm, message.photo[-1].file_id, caption=cap, reply_markup=markup)
        else: bot.send_message(adm, f"{cap}\n📝 {message.text}", reply_markup=markup)
    bot.send_message(uid, "⏳ ደረሰኝዎ እየታየ ነው...")

if __name__ == "__main__":
    load_data()
    keep_alive()
    print("🚀 Fasil Bingo Bot is Ready!")
    bot.remove_webhook()
    while True:
        try: bot.polling(none_stop=True, interval=1, timeout=20)
        except: time.sleep(5)
