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

def get_user(uid, name="ደንበኛ"):
    uid = str(uid)
    if uid not in data["users"]:
        data["users"][uid] = {"name": name, "wallet": 0}
    return data["users"][uid]

def main_menu_markup(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎮 ሰሌዳ ምረጥ", "👤 ፕሮፋይል", "🎫 የያዝኳቸው ቁጥሮች")
    if int(uid) in ADMIN_IDS: markup.add("⚙️ Admin Settings")
    return markup

# --- 4. የሰሌዳ ዲዛይን ---
def update_group_board(b_id):
    board = data["boards"][b_id]
    shift = data.get("current_shift", "me")
    pay = PAYMENTS[shift]
    owner_name = "ፋሲል" if shift == "me" else "ዳመነ"
    
    text = f"🇪🇹 <b>{owner_name} እና {'ዳመነ' if shift=='me' else 'ፋሲል'} 💸💰 online መዝናኛ</b> 🇪🇹\n"
    text += f"          <b>በ {board['price']} ብር ብቻ</b>\n"
    text += f"🏆 <b>ሽልማት፦ {board['prize']}</b>\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"🏦 <b>ገቢ መስገቢያ አማራጮች ({owner_name})</b>\n\n"
    text += f"👉 ቴሌ ብር፦ <code>{pay['tele']}</code>\n"
    text += f"👉 ንግድ ባንክ፦ <code>{pay['cbe']}</code>\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━\n\n"

    for i in range(1, board["max"] + 1):
        num = str(i)
        text += f"{i}👉 <b>{board['slots'][num]}</b> ✅🏆🙏\n" if num in board["slots"] else f"{i}👉 ❤❤❤❤❤\n"

    text += f"\n━━━━━━━━━━━━━━━━━━━━━\n📞 ስልክ፦ {pay['tele']}"

    try:
        final_text = text[:3900]
        if data["pinned_msgs"].get(b_id):
            bot.edit_message_text(final_text, GROUP_ID, data["pinned_msgs"][b_id])
        else:
            m = bot.send_message(GROUP_ID, final_text)
            bot.pin_chat_message(GROUP_ID, m.message_id)
            data["pinned_msgs"][b_id] = m.message_id
            save_data()
    except:
        m = bot.send_message(GROUP_ID, final_text)
        bot.pin_chat_message(GROUP_ID, m.message_id)
        data["pinned_msgs"][b_id] = m.message_id
        save_data()

def process_manual_reg(message):
    try:
        parts = message.text.split('-')
        bid, num, name = parts, parts, parts
        if bid in data["boards"] and num not in data["boards"][bid]["slots"]:
            data["boards"][bid]["slots"][num] = name[:5]
            save_data()
            update_group_board(bid)
            bot.send_message(message.chat.id, f"✅ ሰሌዳ {bid} ቁጥር {num} በ {name} ተይዟል።")
    except:
        bot.send_message(message.chat.id, "⚠️ አጻጻፍ ስህተት! ለምሳሌ፦ 1-15-አበበ")

# --- 5. Handlers ---
@bot.message_handler(commands=['start'])
def welcome(message):
    uid = str(message.chat.id)
    user = get_user(uid, message.from_user.first_name)
    bot.send_message(uid, f"👋 ሰላም {user['name']}! ሂሳብዎ፦ {user['wallet']} ብር", reply_markup=main_menu_markup(uid))

@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    is_admin = call.from_user.id in ADMIN_IDS
    if call.data.startswith('approve_') and is_admin:
        target = call.data.split('_')
        m = bot.send_message(call.from_user.id, f"💵 ለ ID {target} የሚጨመረውን ብር ይጻፉ፦")
        bot.register_next_step_handler(m, finalize_app, target)
    elif call.data.startswith('select_'):
        handle_selection(call)
    elif call.data.startswith('pick_'):
        parts = call.data.split('_')
        if len(parts) == 4:
            bid, num, target_uid = parts, parts, parts
            if str(call.from_user.id) != target_uid:
                bot.answer_callback_query(call.id, "⚠️ ይህ የእርስዎ ምርጫ አይደለም!", show_alert=True)
                return
            finalize_reg_inline(call, bid, num, target_uid)

def finalize_app(message, target):
    try:
        amt = int(message.text)
        uid = str(target)
        user = get_user(uid)
        user["wallet"] += amt
        save_data()
        bot.send_message(uid, f"✅ {amt} ብር ተጨምሯል!")
        
        active_boards = [bid for bid, info in data["boards"].items() if info["active"]]
        if len(active_boards) == 1:
            send_number_buttons(uid, active_boards)
    except:
        bot.send_message(message.chat.id, "⚠️ ስህተት ተፈጥሯል።")

def send_number_buttons(uid, bid):
    board = data["boards"][bid]
    markup = types.InlineKeyboardMarkup(row_width=5)
    btns = [types.InlineKeyboardButton(str(i), callback_data=f"pick_{bid}_{i}_{uid}") 
            for i in range(1, board["max"] + 1) if str(i) not in board["slots"]]
    markup.add(*btns)
    bot.send_message(GROUP_ID, f"🎰 ሰሌዳ {bid} ቁጥር ይምረጡ፦", reply_markup=markup)

def finalize_reg_inline(call, bid, num, uid):
    user = get_user(uid)
    board = data["boards"][bid]
    if user["wallet"] >= board["price"]:
        user["wallet"] -= board["price"]
        board["slots"][num] = user["name"]
        save_data()
        update_group_board(bid)
        bot.answer_callback_query(call.id, f"✅ ቁጥር {num} ተመርጧል!")
        
        if user["wallet"] >= board["price"]:
            send_number_buttons(uid, bid)
        else:
            bot.delete_message(GROUP_ID, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "⚠️ በቂ ሂሳብ የሎትም!")

def handle_selection(call):
    parts = call.data.split('_')
    bid = parts
    uid = parts if len(parts) > 2 else str(call.from_user.id)
    send_number_buttons(uid, bid)

if __name__ == "__main__":
    # ለጊዜው ይህንን ጨምር (አንድ ጊዜ Deploy ካደረግክ በኋላ መልሰህ ብታጠፋው ይሻላል)
    
    save_data()
    
    keep_alive()
    # ... ሌላው የ bot.polling ኮድ ይቀጥላል
    bot.remove_webhook()
    while True:
        try: bot.polling(none_stop=True, interval=1, timeout=20)
        except: time.sleep(5)