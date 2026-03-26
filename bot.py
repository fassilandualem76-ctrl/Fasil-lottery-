import telebot
from telebot import types
import json
import os
from flask import Flask
from threading import Thread
import time
from upstash_redis import Redis

# --- 1. Web Hosting (For Render) ---
app = Flask('')
@app.route('/')
def home(): return "Damene & Fasil Lotto System is Active!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- 2. ቦት እና የዳታቤዝ መረጃዎች ---
TOKEN = "8721334129:AAEbMUHHLcVTv9pGzTwMwC_Wi4tLx3R_F5k"
MY_ID = 8488592165          
ASSISTANT_ID = 7072611117   
GROUP_ID = -1003749311489
DB_CHANNEL_ID = -1003747262103

ADMIN_IDS = [MY_ID, ASSISTANT_ID]

# የአካውንት መረጃዎች (በፈረቃ የተከፋፈሉ)
PAYMENTS = {
    "ዳመነ": {"tele": "0973416038", "cbe": "1000718691323", "owner": "ዳመነ"},
    "ፋሲል": {"tele": "0951381356", "cbe": "1000584461757", "owner": "ፋሲል"}
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
    "current_shift": "ፋሲል",
    "boards": {
        "1": {"max": 25, "price": 50, "prize": "1ኛ 800, 2ኛ 300, 3ኛ 150", "active": True, "slots": {}},
        "2": {"max": 50, "price": 100, "prize": "1ኛ 3000, 2ኛ 1500, 3ኛ 500", "active": True, "slots": {}},
        "3": {"max": 100, "price": 400, "prize": "1ኛ 21,000, 2ኛ 7,000, 3ኛ 3,000", "active": True, "slots": {}}
    },
    "pinned_msgs": {"1": None, "2": None, "3": None}
}

def save_data():
    try:
        redis.set("fasil_lotto_db", json.dumps(data))
        with open(DB_FILE, "w") as f: json.dump(data, f)
        with open(DB_FILE, "rb") as f:
            bot.send_document(DB_CHANNEL_ID, f, caption=f"🔄 Backup - {time.ctime()}")
    except: pass

def load_data():
    global data
    try:
        raw_redis_data = redis.get("fasil_lotto_db")
        if raw_redis_data: data = json.loads(raw_redis_data)
    except: pass

def get_user(uid, name="ደንበኛ"):
    uid = str(uid)
    if uid not in data["users"]: data["users"][uid] = {"name": name, "wallet": 0}
    return data["users"][uid]

def main_menu_markup(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if int(uid) in ADMIN_IDS:
        markup.add("🎮 ሰሌዳ ምረጥ", "👤 ፕሮፋይል", "🎫 የያዝኳቸው ቁጥሮች", "⚙️ Admin Settings")
    return markup

# --- 4. የሰሌዳ ዲዛይን (ልክ እንደ ውቤ መዝናኛ) ---
def update_group_board(b_id):
    board = data["boards"][b_id]
    shift = data.get("current_shift", "ፋሲል")
    pay = PAYMENTS[shift]
    
    text = f"🇪🇹 <b>ዳመነ እና ፋሲል 💸💰 online መዝናኛ</b> 🇪🇹\n"
    text += f"          <b>በ {board['price']} ብር ብቻ</b>\n"
    text += f"      👇👇👇👇👇👇👇👇👇\n"
    text += f"🏆 <b>ሽልማት፦ {board['prize']}</b>\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"🏦 <b>ገቢ መስገቢያ አማራጮች ({shift})</b>\n\n"
    text += f"👉 ቴሌ ብር፦ <code>{pay['tele']}</code>\n"
    text += f"👉 ንግድ ባንክ፦ <code>{pay['cbe']}</code>\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━\n\n"

    for i in range(1, board["max"] + 1):
        num_str = str(i)
        if num_str in board["slots"]:
            text += f"{i}👉 <b>{board['slots'][num_str]}</b> ✅🏆🙏\n"
        else:
            text += f"{i}👉 ❤❤❤❤❤\n"

    text += f"\n━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"🏆 <b>መልካም እድል! USE IT OR LOSE IT</b>\n"
    text += f"🤖 ለመጫወት፦ @Fasil_assistant_bot\n"
    text += f"📞 ስልክ፦ {pay['tele']}"

    try:
        if len(text) > 4000: text = text[:3900] + "\n...ዝርዝሩ ቀጥሏል"
        if data["pinned_msgs"].get(b_id):
            bot.edit_message_text(text, GROUP_ID, data["pinned_msgs"][b_id])
        else:
            m = bot.send_message(GROUP_ID, text)
            bot.pin_chat_message(GROUP_ID, m.message_id)
            data["pinned_msgs"][b_id] = m.message_id
            save_data()
    except:
        m = bot.send_message(GROUP_ID, text)
        bot.pin_chat_message(GROUP_ID, m.message_id)
        data["pinned_msgs"][b_id] = m.message_id
        save_data()

# --- 5. መልዕክት ተቀባዮች (Handlers) ---
@bot.message_handler(commands=['start'])
def welcome(message):
    uid = message.chat.id
    if uid not in ADMIN_IDS and message.chat.type == 'private':
        bot.send_message(uid, "👋 <b>እንኳን ወደ ዳመነ እና ፋሲል መዝናኛ መጡ!</b>\n\nለመጫወት እባክዎ ደረሰኝዎን ግሩፕ ላይ ይላኩ።")
        return
    user = get_user(uid, message.from_user.first_name)
    bot.send_message(uid, f"👋 ሰላም አድሚን {user['name']}! ፈረቃ፦ {data['current_shift']}", reply_markup=main_menu_markup(uid))

@bot.message_handler(commands=['shift'])
def toggle_shift(message):
    if message.from_user.id in ADMIN_IDS:
        data["current_shift"] = "ዳመነ" if data["current_shift"] == "ፋሲል" else "ፋሲል"
        save_data()
        bot.reply_to(message, f"🔄 ፈረቃ ተቀይሯል! ተረኛ፦ {data['current_shift']}")
        # ሰሌዳዎቹን በአዲሱ አካውንት ያድሳል
        for b_id in data["boards"]: update_group_board(b_id)
    else: bot.reply_to(message, "❌ የአድሚን መብት የለዎትም።")

@bot.message_handler(content_types=['photo'])
def handle_receipts(message):
    uid = str(message.from_user.id)
    if int(uid) in ADMIN_IDS and message.chat.type != 'private': return 
    if message.chat.type != 'private':
        bot.reply_to(message, "⏳ <b>ደረሰኝዎ ደርሶኛል!</b>\nአድሚን እስኪያረጋግጥልዎ ድረስ ይጠብቁ። 🙏")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ አፅድቅ", callback_data=f"approve_{uid}"),
               types.InlineKeyboardButton("❌ ውድቅ", callback_data=f"decline_{uid}"))
    cap = f"📩 <b>አዲስ ደረሰኝ</b>\n👤 ከ፦ {message.from_user.first_name}\n🆔 <code>{uid}</code>"
    for adm in ADMIN_IDS:
        try: bot.send_photo(adm, message.photo[-1].file_id, caption=cap, reply_markup=markup)
        except: pass

@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    is_admin = call.from_user.id in ADMIN_IDS
    if call.data.startswith('approve_') and is_admin:
        target = call.data.split('_')
        m = bot.send_message(call.from_user.id, f"💵 ለ ID {target} የሚጨመረውን ብር ይጻፉ፦")
        bot.register_next_step_handler(m, finalize_app, target)
    
    elif call.data == "admin_manual_reg" and is_admin:
        m = bot.send_message(call.from_user.id, "📝 <b>በአካል መመዝገቢያ</b>\nይህን ይከተሉ፦ ሰሌዳ-ቁጥር-ስም\n(ለምሳሌ: 3-15-አበበ)")
        bot.register_next_step_handler(m, process_manual_reg)

    elif call.data.startswith('pick_'):
        _, bid, num = call.data.split('_')
        uid = str(call.from_user.id); user = get_user(uid, call.from_user.first_name)
        board = data["boards"][bid]
        if user["wallet"] >= board["price"]:
            data["users"][uid]["wallet"] -= board["price"]
            board["slots"][num] = user["name"][:5]
            save_data(); update_group_board(bid)
            bot.edit_message_text(f"✅ <b>ቁጥር {num} በ {user['name']} ተይዟል!</b>", call.message.chat.id, call.message.message_id, reply_markup=None)
        else: bot.answer_callback_query(call.id, "⚠️ በቂ ሂሳብ የሎትም!", show_alert=True)

@bot.message_handler(func=lambda m: m.text == "⚙️ Admin Settings" and m.from_user.id in ADMIN_IDS)
def admin_panel(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("📝 በአካል መዝግብ (Cash)", callback_data="admin_manual_reg"),
               types.InlineKeyboardButton("⚙️ ሰሌዳዎችን አስተካክል", callback_data="admin_manage"),
               types.InlineKeyboardButton("🔄 ሰሌዳ አጽዳ (Reset)", callback_data="admin_reset"))
    bot.send_message(message.chat.id, "🛠 <b>የአድሚን ዳሽቦርድ</b>", reply_markup=markup)

def finalize_app(message, target):
    try:
        amt = int(message.text); uid = str(target); user = get_user(uid)
        user["wallet"] += amt; save_data()
        bot.send_message(target, f"✅ <b>{amt} ብር ተረጋግጧል!</b>")
        # ግሩፕ ላይ ቁጥር እንዲመርጥ በተን ይልካል
        active_boards = [bid for bid, info in data["boards"].items() if info["active"]]
        markup = types.InlineKeyboardMarkup()
        for bid in active_boards: markup.add(types.InlineKeyboardButton(f"ሰሌዳ {bid}", callback_data=f"select_{bid}_{uid}"))
        bot.send_message(GROUP_ID, f"✅ <a href='tg://user?id={uid}'>ተጠቃሚ</a> ክፍያዎ ጸድቋል! እባክዎ ሰሌዳ ይምረጡ፦", reply_markup=markup)
    except: bot.send_message(message.chat.id, "⚠️ ስህተት!")

def process_manual_reg(message):
    try:
        parts = message.text.split('-')
        bid, num, name = parts, parts, parts[:5]
        if bid in data["boards"] and num not in data["boards"][bid]["slots"]:
            data["boards"][bid]["slots"][num] = name
            save_data(); update_group_board(bid)
            bot.send_message(message.chat.id, f"✅ ሰሌዳ {bid} ቁጥር {num} በ {name} ተይዟል።")
        else: bot.send_message(message.chat.id, "⚠️ ስህተት!")
    except: bot.send_message(message.chat.id, "⚠️ አጻጻፍ፦ 1-15-አበበ")

# --- 6. ቦቱን ማስነሻ --
if __name__ == "__main__":
    # 1. ዳታቤዙን መጀመሪያ እንዲያነብ እናረጋግጣለን
    load_data()
    
    # 2. Render ላይ ቦቱ እንዳይተኛ (Sleep) የሚያደርገው Web Server ይነሳል
    keep_alive()
    
    # 3. የድሮ Webhook ካለ ይጸዳል
    bot.remove_webhook()
    
    print("🚀 Fasil Bingo Bot is now Active and Running!")
    
    # 4. ቦቱ ሳይቆም እንዲቀጥል (Error ቢፈጠር እንኳ ራሱን እንዲቀሰቅስ)
    while True:
        try:
            bot.polling(none_stop=True, interval=2, timeout=20)
        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(5) # ስህተት ሲፈጠር ለ5 ሰከንድ አርፎ እንዲነሳ


