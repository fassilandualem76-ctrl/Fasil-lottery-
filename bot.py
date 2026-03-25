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

# --- 4. ረዳት ተግባራት ---
def get_user(uid, name="ደንበኛ"):
    uid = str(uid)
    if uid not in data["users"]:
        data["users"][uid] = {"name": name, "wallet": 0}
    return data["users"][uid]

def main_menu_markup(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎮 ሰሌዳ ምረጥ", "👤 ፕሮፋይል")
    markup.add("🎫 የያዝኳቸው ቁጥሮች", "🔗 የግብዣ ሊንክ") # ግብዣ እዚህ ተጨምሯል
    if int(uid) in ADMIN_IDS: markup.add("⚙️ Admin Settings")
    return markup

def update_group_board(b_id):
    board = data["boards"][b_id]
    text = f"🎰 <b>ፋሲል ዕጣ - ሰሌዳ {b_id} (1-{board['max']})</b>\n"
    text += f"🎫 መደብ፦ <b>{board['price']} ብር</b>\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━\n"
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
    text += f"━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"🎁 <b>ሽልማት፦ {board['prize']}</b>\n"
    try:
        if data["pinned_msgs"].get(b_id):
            bot.edit_message_text(text, GROUP_ID, data["pinned_msgs"][b_id])
        else:
            m = bot.send_message(GROUP_ID, text)
            bot.pin_chat_message(GROUP_ID, m.message_id)
            data["pinned_msgs"][b_id] = m.message_id
            save_data()
    except: pass

# --- 5. ዋና ዋና ትዕዛዞች & የግብዣ ሲስተም ---
@bot.message_handler(commands=['start'])
def welcome(message):
    uid = str(message.chat.id)
    text_split = message.text.split()
    
    # የግብዣ ሲስተም (Referral Logic)
    if len(text_split) > 1 and uid not in data["users"]:
        referrer_id = text_split
        if referrer_id != uid and referrer_id in data["users"]:
            data["users"][referrer_id]["wallet"] += 1
            save_data()
            try: bot.send_message(referrer_id, "🎉 በግብዣዎ አዲስ ሰው ስለመጣ 1 ብር ተጨምሮልዎታል!")
            except: pass

    user = get_user(uid, message.from_user.first_name)
    active_pay = PAYMENTS[data.get("current_shift", "me")]
    welcome_text = (f"👋 <b>እንኳን ወደ ፋሲል መዝናኛ መጡ!</b>\n\n💰 <b>ቀሪ ሂሳብ፦</b> {user['wallet']} ብር\n"
                    f"🏦 <b>Telebirr:</b> <code>{active_pay['tele']}</code>\n🔸 <b>CBE:</b> <code>{active_pay['cbe']}</code>")
    bot.send_message(uid, welcome_text, reply_markup=main_menu_markup(uid))

@bot.message_handler(func=lambda m: m.text == "🔗 የግብዣ ሊንክ")
def send_invite_link(message):
    bot_username = bot.get_me().username
    link = f"https://t.me/{bot_username}?start={message.chat.id}"
    bot.send_message(message.chat.id, f"🎁 <b>የግብዣ ሊንክዎ፦</b>\n\n<code>{link}</code>\n\nበዚህ ሊንክ ሰዎችን ሲጋብዙ ለእያንዳንዱ ሰው <b>1 ብር</b> ያገኛሉ!")

# --- 6. የአድሚን ትዕዛዞች (Unpaid ማስወገጃ) ---
@bot.message_handler(commands=['warn_unpaid'])
def warn_unpaid(message):
    if message.from_user.id not in ADMIN_IDS: return
    count = 0
    for bid, binfo in data["boards"].items():
        for num, uname in binfo["slots"].items():
            target_id = next((uid for uid, info in data["users"].items() if info["name"] == uname), None)
            if target_id:
                try:
                    bot.send_message(target_id, f"⚠️ <b>ማስጠንቀቂያ!</b>\nበሰሌዳ {bid} የያዙት ቁጥር {num} ክፍያ ስላልተፈጸመ ሊሰረዝ ነው።")
                    count += 1
                except: pass
    bot.reply_to(message, f"📢 ለ {count} ሰዎች ማስጠንቀቂያ ተልኳል።")

@bot.message_handler(commands=['remove_unpaid'])
def remove_unpaid(message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        args = message.text.split() # /remove_unpaid 1-15
        bid, num = args.split('-')
        if bid in data["boards"] and num in data["boards"][bid]["slots"]:
            uname = data["boards"][bid]["slots"].pop(num)
            save_data(); update_group_board(bid)
            bot.reply_to(message, f"✅ ተጫዋች {uname} ከሰሌዳ {bid} ቁጥር {num} ተወግዷል።")
        else: bot.reply_to(message, "⚠️ ቁጥሩ አልተገኘም።")
    except: bot.reply_to(message, "አጠቃቀም፦ <code>/remove_unpaid 1-15</code>")

# --- 7. የደረሰኝ መቀበያ (መጨረሻ ላይ መሆን አለበት) ---
@bot.message_handler(content_types=['photo', 'text'])
def handle_receipts(message):
    if message.chat.type != 'private': return 
    # በተኖችን እንደ ደረሰኝ እንዳይቆጥር መከላከያ
    if message.text in ["🎮 ሰሌዳ ምረጥ", "👤 ፕሮፋይል", "⚙️ Admin Settings", "🎫 የያዝኳቸው ቁጥሮች", "🔗 የግብዣ ሊንክ"]:
        return

    uid = str(message.chat.id)
    bot.send_message(uid, "⏳ <b>ደረሰኝዎ ደርሶኛል...</b>\nእባክዎ እስኪረጋገጥ ይጠብቁ። 🙏")
    
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("✅ አፅድቅ", callback_data=f"approve_{uid}"),
               types.InlineKeyboardButton("❌ ውድቅ", callback_data=f"decline_{uid}"))
    
    cap = f"📩 <b>አዲስ ደረሰኝ</b>\n👤 <b>ከ፦</b> {message.from_user.first_name}\n🆔 <b>ID፦</b> <code>{uid}</code>"
    for adm in ADMIN_IDS:
        try:
            if message.photo: bot.send_photo(adm, message.photo[-1].file_id, caption=cap, reply_markup=markup)
            else: bot.send_message(adm, f"{cap}\n📝 <b>ዝርዝር፦</b>\n<code>{message.text}</code>", reply_markup=markup)
        except: pass

# --- 8. Callback Logic (ያልተቀየረ) ---
@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    is_admin = call.from_user.id in ADMIN_IDS
    if call.data.startswith('approve_') and is_admin:
        target = call.data.split('_')
        m = bot.send_message(call.from_user.id, f"💵 ለ ID {target} የሚጨመረውን ብር ይጻፉ፦")
        bot.register_next_step_handler(m, finalize_app, target)
    elif call.data.startswith('decline_') and is_admin:
        target = call.data.split('_')
        m = bot.send_message(call.from_user.id, "❌ ውድቅ የተደረገበትን ምክንያት ይጻፉ፦")
        bot.register_next_step_handler(m, finalize_dec, target)
    elif call.data.startswith('select_'): handle_selection(call)
    elif call.data.startswith('pick_'):
        _, bid, num = call.data.split('_')
        finalize_reg_inline(call, bid, num)
    elif call.data == "lookup_winner" and is_admin:
        m = bot.send_message(call.from_user.id, "አሸናፊ ለመፈለግ ሰሌዳ እና ቁጥር ይጻፉ (ለምሳሌ: 2-13)፦")
        bot.register_next_step_handler(m, process_lookup)
    elif call.data == "admin_manage" and is_admin: manage_menu(call)
    elif call.data.startswith('edit_') and is_admin: edit_board(call)
    elif call.data.startswith('toggle_') and is_admin:
        bid = call.data.split('_')
        data["boards"][bid]["active"] = not data["boards"][bid]["active"]
        save_data(); edit_board(call)
    elif call.data.startswith('set_') and is_admin:
        _, action, bid = call.data.split('_')
        m = bot.send_message(call.from_user.id, f"የሰሌዳ {bid} አዲስ ዋጋ/ሽልማት ይጻፉ፦")
        bot.register_next_step_handler(m, update_board_value, bid, action)
    elif call.data == "admin_reset" and is_admin: reset_menu(call)
    elif call.data.startswith('doreset_') and is_admin:
        bid = call.data.split('_')
        data["boards"][bid]["slots"] = {}; data["pinned_msgs"][bid] = None
        save_data(); bot.answer_callback_query(call.id, "ሰሌዳው ጸድቷል!"); update_group_board(bid)

def finalize_app(message, target):
    try:
        amt = int(message.text)
        data["users"][str(target)]["wallet"] += amt
        save_data()
        bot.send_message(target, f"✅ <b>{amt} ብር ተጨምሯል!</b>")
        m = bot.send_message(target, "አሁን በሰሌዳ ላይ የሚወጣውን ስምዎን (እስከ 5 ፊደል) ይጻፉ፦")
        bot.register_next_step_handler(m, save_name, target)
    except: bot.send_message(message.chat.id, "⚠️ ስህተት!")

def save_name(message, uid):
    data["users"][str(uid)]["name"] = message.text[:5]
    save_data()
    bot.send_message(uid, f"✅ ስምዎ '{message.text[:5]}' ተመዝግቧል!")

def finalize_dec(message, target): bot.send_message(target, f"❌ ደረሰኝዎ ውድቅ ሆኗል። ምክንያት፦ {message.text}")

def handle_selection(call):
    bid = call.data.split('_'); user = get_user(call.message.chat.id)
    board = data["boards"][bid]
    if user["wallet"] < board["price"]:
        bot.answer_callback_query(call.id, "⚠️ በቂ ሂሳብ የሎትም!", show_alert=True); return
    markup = types.InlineKeyboardMarkup(row_width=5)
    btns = [types.InlineKeyboardButton(str(i), callback_data=f"pick_{bid}_{i}") for i in range(1, board["max"] + 1) if str(i) not in board["slots"]]
    markup.add(*btns)
    bot.edit_message_text(f"🎰 <b>ሰሌዳ {bid}</b>\nቁጥር ይምረጡ፦", call.message.chat.id, call.message.message_id, reply_markup=markup)

def finalize_reg_inline(call, bid, num):
    uid = str(call.message.chat.id); user = get_user(uid); board = data["boards"][bid]
    if user["wallet"] < board["price"]: return
    data["users"][uid]["wallet"] -= board["price"]
    board["slots"][num] = user["name"]
    save_data(); update_group_board(bid); bot.answer_callback_query(call.id, f"✅ ቁጥር {num} ተመርጧል!")

def manage_menu(call):
    markup = types.InlineKeyboardMarkup()
    for bid in data["boards"]: markup.add(types.InlineKeyboardButton(f"ሰሌዳ {bid}", callback_data=f"edit_{bid}"))
    bot.edit_message_text("ሰሌዳ ይምረጡ፦", call.from_user.id, call.message.message_id, reply_markup=markup)

def edit_board(call):
    bid = call.data.split('_'); b = data["boards"][bid]
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton(f"{'🟢 ክፍት' if b['active'] else '🔴 ዝግ'}", callback_data=f"toggle_{bid}"))
    markup.add(types.InlineKeyboardButton("🎫 ዋጋ", callback_data=f"set_price_{bid}"), types.InlineKeyboardButton("🎁 ሽልማት", callback_data=f"set_prize_{bid}"))
    bot.edit_message_text(f"📊 ሰሌዳ {bid}", call.from_user.id, call.message.message_id, reply_markup=markup)

def update_board_value(message, bid, action):
    try:
        if action == "price": data["boards"][bid]["price"] = int(message.text)
        else: data["boards"][bid]["prize"] = message.text
        save_data(); update_group_board(bid); bot.send_message(message.chat.id, "✅ ተቀይሯል!")
    except: pass

def reset_menu(call):
    markup = types.InlineKeyboardMarkup()
    for bid in data["boards"]: markup.add(types.InlineKeyboardButton(f"Reset {bid}", callback_data=f"doreset_{bid}"))
    bot.send_message(call.from_user.id, "የትኛው ሰሌዳ ይጽዳ?", reply_markup=markup)

# --- 9. ማስጀመር ---
if __name__ == "__main__":
    keep_alive()
    bot.remove_webhook()
    while True:
        try: bot.polling(none_stop=True, interval=1, timeout=20)
        except: time.sleep(5)
