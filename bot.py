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
def home(): return "Fasil & Damene System is Active!"

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

# --- የክፍያ መረጃ (Shift System) ---
PAYMENTS = {
    "ፋሲል": {
        "text": "👉 ንግድ ባንክ 1000584461757\n👉 ቴሌ ብር 0951381356",
        "tele": "0951381356", 
        "cbe": "1000584461757"
    },
    "ዳመነ": {
        "text": "👉 ንግድ ባንክ 1000718691323\n👉 ቴሌ ብር 0973416038",
        "tele": "0973416038", 
        "cbe": "1000718691323"
    }
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
        "1": {"max": 100, "price": 400, "prize": "1ኛ 21,000, 2ኛ 7,000, 3ኛ 3,000", "active": True, "slots": {}}
    },
    "pinned_msgs": {"1": None}
}

def save_data():
    try:
        redis.set("fasil_lotto_db", json.dumps(data))
        with open(DB_FILE, "w") as f:
            json.dump(data, f)
    except: pass

def load_data():
    global data
    try:
        raw_redis_data = redis.get("fasil_lotto_db")
        if raw_redis_data:
            data = json.loads(raw_redis_data)
        elif os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f:
                data.update(json.load(f))
    except: pass

load_data()

def get_user(uid, name="ደንበኛ"):
    uid = str(uid)
    if uid not in data["users"]:
        data["users"][uid] = {"name": name, "wallet": 0}
    return data["users"][uid]

# --- 4. የሰሌዳ ዲዛይን (ውቤ ዲዛይን) ---
def update_group_board(b_id):
    board = data["boards"].get(b_id)
    if not board: return
    
    shift = data.get("current_shift", "ፋሲል")
    acc_info = PAYMENTS[shift]["text"]
    
    text = f"<b>🇪🇹 ዳመነ እና ፋሲል 💸💰 online መዝናኛ 🇪🇹</b>\n"
    text += f"              <b>በ{board['price']} ብር</b>\n"
    text += f"              👇👇👇👇👇\n"
    text += f"      <b>{board['prize']}</b>\n\n"
    text += f"☎️ 0910984771\n\n"
    text += f"      <b>ገቢ መስገቢያ አማራጮች</b>\n"
    text += f"      👇👇👇👇👇\n"
    text += f"{acc_info}\n\n"
    
    line = ""
    for i in range(1, board["max"] + 1):
        s_i = str(i)
        if s_i in board["slots"]:
            u_name = board["slots"][s_i]
            line += f"<b>{s_i}👉{u_name}✅🏆🙏</b>\n"
        else:
            line += f"<b>{s_i}👉⬜️⬜️⬜️⬜️</b>\n"
    
    text += line
    text += f"\n🏆 መልካም እድል! ቁጥር ይዞ ገቢ ማድረግ የግድ ነው።"

    try:
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

# --- 5. ዋና ትዕዛዞች ---

# Manual Entry (1-15-አበበ)
@bot.message_handler(func=lambda m: m.chat.id == GROUP_ID and "-" in m.text and m.from_user.id in ADMIN_IDS)
def manual_entry(message):
    try:
        bid, num, name = message.text.split("-")
        if bid in data["boards"]:
            data["boards"][bid]["slots"][num] = name
            save_data()
            update_group_board(bid)
            bot.reply_to(message, f"✅ ሰሌዳ {bid} ቁጥር {num} በ {name} ተመዝግቧል!")
    except: pass

@bot.message_handler(commands=['shift'])
def toggle_shift(message):
    if message.from_user.id in ADMIN_IDS:
        data["current_shift"] = "ዳመነ" if data.get("current_shift") == "ፋሲል" else "ፋሲል"
        save_data()
        bot.reply_to(message, f"🔄 ፈረቃ ተቀይሯል! አሁን ተረኛው፦ <b>{data['current_shift']}</b>")
        for b_id in data["boards"]: update_group_board(b_id)
    else:
        bot.reply_to(message, "❌ የአድሚን መብት የለዎትም።")

@bot.message_handler(commands=['start'])
def welcome(message):
    uid = str(message.chat.id)
    user = get_user(uid, message.from_user.first_name)
    shift = data.get("current_shift", "ፋሲል")
    acc = PAYMENTS[shift]
    
    welcome_text = (
        f"👋 <b>እንኳን ወደ {data['current_shift']} እና ፋሲል መዝናኛ መጡ!</b>\n\n"
        f"💰 <b>ቀሪ ሂሳብ፦</b> {user['wallet']} ብር\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏦 <b>ክፍያ ለመፈጸም፦</b>\n{acc['text']}\n\n"
        f"⚠️ <b>ብር ሲያስገቡ ደረሰኝ እዚህ ይላኩ።</b>"
    )
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎮 ሰሌዳ ምረጥ", "👤 ፕሮፋይል")
    bot.send_message(uid, welcome_text, reply_markup=markup)

@bot.message_handler(content_types=['photo', 'text'])
def handle_receipts(message):
    if message.chat.type != 'private': return 
    if message.text in ["🎮 ሰሌዳ ምረጥ", "👤 ፕሮፋይል"]: return
    
    uid = str(message.chat.id)
    bot.send_message(uid, "⏳ <b>ደረሰኝዎ ደርሶኛል...</b>\nአድሚን እስኪያጸድቅ ይጠብቁ።")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ አፅድቅ", callback_data=f"approve_{uid}"),
               types.InlineKeyboardButton("❌ ውድቅ", callback_data=f"decline_{uid}"))
    
    cap = f"📩 <b>አዲስ ደረሰኝ</b>\n👤 ከ፦ {message.from_user.first_name}\n🆔 ID፦ <code>{uid}</code>"
    for adm in ADMIN_IDS:
        if message.photo: bot.send_photo(adm, message.photo[-1].file_id, caption=cap, reply_markup=markup)
        else: bot.send_message(adm, f"{cap}\n📝 ዝርዝር፦ {message.text}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    if call.data.startswith('approve_'):
        target = call.data.split('_')
        m = bot.send_message(call.from_user.id, f"💵 ለ ID {target} የሚጨመረውን ብር ይጻፉ፦")
        bot.register_next_step_handler(m, finalize_app, target)
    
    elif call.data.startswith('pick_'):
        _, bid, num = call.data.split('_')
        finalize_reg(call, bid, num)

def finalize_app(message, target):
    try:
        amt = int(message.text)
        data["users"][str(target)]["wallet"] += amt
        save_data()
        bot.send_message(target, f"✅ <b>{amt} ብር ተቀብያለሁ!</b>\nአሁን ቁጥር ይምረጡ።")
        
        # --- Auto-Display Buttons ---
        # ክፍያው እንደጸደቀ በራሱ ምርጫውን ያመጣለታል
        show_inline_numbers(target)
    except: bot.send_message(message.chat.id, "⚠️ ቁጥር ብቻ ይጻፉ።")

def show_inline_numbers(uid):
    # ለጊዜው ሰሌዳ 1ን በራሱ ያሳያል
    bid = "1"
    board = data["boards"][bid]
    user = data["users"][str(uid)]
    
    markup = types.InlineKeyboardMarkup(row_width=5)
    btns = []
    for i in range(1, board["max"] + 1):
        if str(i) not in board["slots"]:
            btns.append(types.InlineKeyboardButton(str(i), callback_data=f"pick_{bid}_{i}"))
    
    markup.add(*btns)
    bot.send_message(uid, f"🎰 <b>ሰሌዳ {bid}</b>\n💰 ቀሪ ሂሳብ፦ {user['wallet']} ብር\n\nየሚፈልጉትን ቁጥር ይጫኑ፦", reply_markup=markup)

def finalize_reg(call, bid, num):
    uid = str(call.message.chat.id)
    user = get_user(uid)
    board = data["boards"][bid]
    
    if user["wallet"] < board["price"]:
        bot.answer_callback_query(call.id, "⚠️ በቂ ሂሳብ የሎትም!", show_alert=True)
        return

    data["users"][uid]["wallet"] -= board["price"]
    board["slots"][num] = user["name"]
    save_data()
    update_group_board(bid)
    
    bot.answer_callback_query(call.id, f"✅ ቁጥር {num} ተመርጧል!")
    
    if user["wallet"] >= board["price"]:
        # ገና ብር ካለው በድጋሚ ቁጥር እንዲመርጥ ባተኑን አድሶ ያሳየዋል
        show_inline_numbers(uid)
    else:
        bot.edit_message_text(f"✅ ምዝገባ ተጠናቋል።\n💰 ቀሪ ሂሳብ፦ {user['wallet']} ብር", uid, call.message.message_id)

@bot.message_handler(func=lambda m: m.text == "🎮 ሰሌዳ ምረጥ")
def manual_select(message):
    show_inline_numbers(message.chat.id)

@bot.message_handler(func=lambda m: m.text == "👤 ፕሮፋይል")
def show_profile(message):
    user = get_user(message.chat.id)
    bot.send_message(message.chat.id, f"👤 <b>ፕሮፋይል</b>\n📛 ስም፦ {user['name']}\n💰 ቀሪ፦ {user['wallet']} ብር")

if __name__ == "__main__":
    keep_alive()
    bot.remove_webhook()
    print("Bot is running...")
    bot.polling(none_stop=True)
