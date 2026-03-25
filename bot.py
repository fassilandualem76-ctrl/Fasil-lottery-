import telebot
from telebot import types
import json
import os
from flask import Flask
from threading import Thread
import time
from upstash_redis import Redis

# --- 1. Web Hosting ---
app = Flask('')
@app.route('/')
def home(): return "Fasil Lotto System is Active!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- 2. ቦት መረጃዎች ---
TOKEN = "8721334129:AAEbMUHHLcVTv9pGzTwMwC_Wi4tLx3R_F5k"
MY_ID = 8488592165          
ASSISTANT_ID = 7072611117   
GROUP_ID = -1003749311489
DB_CHANNEL_ID = -1003747262103

ADMIN_IDS = [MY_ID, ASSISTANT_ID]

PAYMENTS = {
    "me": {"tele": "0951381356", "cbe": "1000584461757"},
    "assistant": {"tele": "0973416038", "cbe": "1000718691323"}
}

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# Redis Connection
REDIS_URL = "https://sunny-ferret-79578.upstash.io"
REDIS_TOKEN = "gQAAAAAAATbaAAIncDE4MTQ2MThjMjVjYjI0YzU5OGQ0MjMzZGI0MGIwZTkwNXAxNzk1Nzg"
redis = Redis(url=REDIS_URL, token=REDIS_TOKEN)

# --- 3. ዳታቤዝ አያያዝ ---
DB_FILE = "fasil_db.json"
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
        redis.set("fasil_lotto_db", json.dumps(data))
        with open(DB_FILE, "w") as f:
            json.dump(data, f)
        with open(DB_FILE, "rb") as f:
            bot.send_document(DB_CHANNEL_ID, f, caption=f"🔄 Database Backup - {time.ctime()}")
    except: pass

def load_data():
    global data
    try:
        raw_redis_data = redis.get("fasil_lotto_db")
        if raw_redis_data:
            data = json.loads(raw_redis_data)
        elif os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f:
                loaded = json.load(f)
                data.update(loaded)
    except: pass

load_data()

# --- 4. ረዳት ፋንክሽኖች ---
def get_user(uid, name="ደንበኛ"):
    uid = str(uid)
    if uid not in data["users"]:
        data["users"][uid] = {"name": name, "wallet": 0}
    return data["users"][uid]

def main_menu_markup(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎮 ሰሌዳ ምረጥ", "👤 ፕሮፋይል")
    markup.add("🎫 የያዝኳቸው ቁጥሮች", "🔗 የግብዣ ሊንክ")
    if int(uid) in ADMIN_IDS: markup.add("⚙️ Admin Settings")
    return markup

def show_main_menu(uid):
    bot.send_message(uid, "<b>ዋና ማውጫ፦</b>", reply_markup=main_menu_markup(uid))

def update_group_board(b_id):
    board = data["boards"][b_id]
    text = f"🎰 <b>ፋሲል ዕጣ - ሰሌዳ {b_id}</b>\n━━━━━━━━━━━━━━━━━━━━━\n"
    line = ""
    for i in range(1, board["max"] + 1):
        s_i = str(i).zfill(2)
        if str(i) in board["slots"]:
            line += f"<code>{s_i}</code>✅{board['slots'][str(i)][:5]}\t\t"
        else:
            line += f"<code>{s_i}</code>⬜️\t\t"
        if i % 2 == 0:
            text += line + "\n"
            line = ""
    text += line
    try:
        if data["pinned_msgs"].get(b_id):
            bot.edit_message_text(text, GROUP_ID, data["pinned_msgs"][b_id])
        else:
            m = bot.send_message(GROUP_ID, text)
            bot.pin_chat_message(GROUP_ID, m.message_id)
            data["pinned_msgs"][b_id] = m.message_id
            save_data()
    except: pass

# --- 5. የአድሚን ልዩ ትዕዛዞች (ማስጠንቀቂያ እና ስረዛ) ---
@bot.message_handler(commands=['warn_unpaid'])
def warn_unpaid(message):
    if message.from_user.id not in ADMIN_IDS: return
    count = 0
    for bid, binfo in data["boards"].items():
        for num, uname in binfo["slots"].items():
            target_id = next((uid for uid, info in data["users"].items() if info["name"] == uname), None)
            if target_id:
                try:
                    bot.send_message(target_id, f"⚠️ <b>ማስጠንቀቂያ!</b>\nበሰሌዳ {bid} የያዙት ቁጥር {num} ክፍያ ስላልተፈጸመበት ሊሰረዝ ነው።")
                    count += 1
                except: pass
    bot.reply_to(message, f"📢 ለ {count} ሰዎች ማስጠንቀቂያ ተልኳል።")

@bot.message_handler(commands=['remove_unpaid'])
def remove_unpaid(message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        args = message.text.split()
        bid, num = args.split('-')
        if num in data["boards"][bid]["slots"]:
            uname = data["boards"][bid]["slots"].pop(num)
            save_data(); update_group_board(bid)
            bot.reply_to(message, f"✅ {uname} ተሰርዟል።")
    except: bot.reply_to(message, "አጠቃቀም፦ /remove_unpaid 1-15")

# --- 6. ዋና ዋና ትዕዛዞች ---
@bot.message_handler(commands=['start'])
def welcome(message):
    uid = str(message.chat.id)
    text_split = message.text.split()
    if len(text_split) > 1 and uid not in data["users"]:
        referrer_id = text_split # ✅ የሪፈራል ማስተካከያ
        if referrer_id != uid and referrer_id in data["users"]:
            data["users"][referrer_id]["wallet"] += 1
            save_data()
            try: bot.send_message(referrer_id, "🎉 በግብዣዎ አዲስ ሰው ስለመጣ 1 ብር ተጨምሯል።")
            except: pass
    user = get_user(uid, message.from_user.first_name)
    bot.send_message(uid, f"👋 እንኳን መጡ! ቀሪ ሂሳብ፦ {user['wallet']} ብር")
    show_main_menu(uid)

@bot.message_handler(func=lambda m: m.text == "🔗 የግብዣ ሊንክ")
def send_link(message):
    bot_username = bot.get_me().username
    link = f"https://t.me/{bot_username}?start={message.chat.id}"
    bot.send_message(message.chat.id, f"🎁 የግብዣ ሊንክዎ፦\n<code>{link}</code>")

# --- 7. Handle Receipts ---
@bot.message_handler(content_types=['photo', 'text'])
def handle_receipts(message):
    if message.chat.type != 'private': return 
    # ✅ በተኖቹን እንደ ደረሰኝ እንዳይቆጥር መከላከል
    if message.text in ["🎮 ሰሌዳ ምረጥ", "👤 ፕሮፋይል", "⚙️ Admin Settings", "🎫 የያዝኳቸው ቁጥሮች", "🔗 የግብዣ ሊንክ"]: return
    uid = str(message.chat.id)
    bot.send_message(uid, "⏳ ደረሰኝዎ ለባለቤቱ ተልኳል...")
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("✅ አፅድቅ", callback_data=f"approve_{uid}"),
               types.InlineKeyboardButton("❌ ውድቅ", callback_data=f"decline_{uid}"))
    for adm in ADMIN_IDS:
        try:
            if message.photo: bot.send_photo(adm, message.photo[-1].file_id, caption=f"ID: {uid}", reply_markup=markup)
            else: bot.send_message(adm, f"ID: {uid}\n📝 {message.text}", reply_markup=markup)
        except: pass

@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    if call.data.startswith('approve_'):
        target = call.data.split('_')
        m = bot.send_message(call.from_user.id, f"ለ ID {target} የሚጨመረውን ብር ይጻፉ፦")
        bot.register_next_step_handler(m, finalize_app, target)
    elif call.data.startswith('select_'): handle_selection(call)
    elif call.data.startswith('pick_'):
        _, bid, num = call.data.split('_')
        finalize_reg_inline(call, bid, num)

def finalize_app(message, target):
    try:
        amt = int(message.text)
        data["users"][str(target)]["wallet"] += amt
        save_data()
        bot.send_message(target, f"✅ {amt} ብር ተጨምሯል።")
    except: pass

def handle_selection(call):
    bid = call.data.split('_')
    board = data["boards"][bid]
    markup = types.InlineKeyboardMarkup(row_width=5)
    btns = [types.InlineKeyboardButton(str(i), callback_data=f"pick_{bid}_{i}") for i in range(1, board["max"] + 1) if str(i) not in board["slots"]]
    markup.add(*btns)
    bot.edit_message_text(f"🎰 ሰሌዳ {bid} - ቁጥር ይምረጡ፦", call.message.chat.id, call.message.message_id, reply_markup=markup)

def finalize_reg_inline(call, bid, num):
    uid = str(call.message.chat.id); user = get_user(uid); board = data["boards"][bid]
    if user["wallet"] < board["price"]: 
        bot.answer_callback_query(call.id, "⚠️ በቂ ሂሳብ የሎትም!"); return
    data["users"][uid]["wallet"] -= board["price"]
    board["slots"][num] = user["name"]
    save_data(); update_group_board(bid)
    bot.answer_callback_query(call.id, f"✅ ቁጥር {num} ተመርጧል!")

# --- 8. ቦቱን ማስጀመር ---
if __name__ == "__main__":
    keep_alive()
    bot.remove_webhook()
    while True:
        try: bot.polling(none_stop=True, interval=1, timeout=20)
        except: time.sleep(5)
