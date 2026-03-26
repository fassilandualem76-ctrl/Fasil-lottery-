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
    "me": {"tele": "0951381356", "cbe": "1000584461757", "name": "ፋሲል"},
    "assistant": {"tele": "0973416038", "cbe": "1000718691323", "name": "ዳመነ"}
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
                data.update(json.load(f))
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
    
    text = f"🇪🇹 <b>ዳመነ እና ፋሲል 💸💰 online መዝናኛ</b> 🇪🇹\n"
    text += f"          <b>በ {board['price']} ብር ብቻ</b>\n"
    text += f"      👇👇👇👇👇👇👇👇👇\n"
    text += f"🏆 <b>ሽልማት፦ {board['prize']}</b>\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"🏦 <b>ገቢ መስገቢያ አማራጮች ({pay['name']})</b>\n\n"
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

# --- 5. ትዕዛዞች ---
@bot.message_handler(commands=['start'])
def welcome(message):
    uid = str(message.chat.id)
    user = get_user(uid, message.from_user.first_name)
    active_pay = PAYMENTS[data.get("current_shift", "me")]
    welcome_text = (
        f"👋 <b>እንኳን ወደ ፋሲል መዝናኛና ዕድለኛ ዕጣ መጡ!</b>\n\n"
        f"👤 <b>ስም፦</b> {user['name']}\n"
        f"💰 <b>ቀሪ ሂሳብ፦</b> {user['wallet']} ብር\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏦 <b>Telebirr:</b> <code>{active_pay['tele']}</code>\n"
        f"🔸 <b>CBE:</b> <code>{active_pay['cbe']}</code>\n"
    )
    bot.send_message(uid, welcome_text, reply_markup=main_menu_markup(uid))

@bot.message_handler(commands=['shift'])
def toggle_shift(message):
    if message.from_user.id == MY_ID:
        data["current_shift"] = "assistant" if data["current_shift"] == "me" else "me"
        save_data()
        bot.reply_to(message, f"🔄 ፈረቃ ተቀይሯል! አሁን ተረኛው፦ {data['current_shift']}")

@bot.message_handler(content_types=['photo', 'text'])
def handle_receipts(message):
    uid = str(message.from_user.id)
    if message.from_user.is_bot: return
    if message.text in ["🎮 ሰሌዳ ምረጥ", "👤 ፕሮፋይል", "⚙️ Admin Settings", "🎫 የያዝኳቸው ቁጥሮች"]: return

    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("✅ አፅድቅ", callback_data=f"approve_{uid}"),
               types.InlineKeyboardButton("❌ ውድቅ", callback_data=f"decline_{uid}"))
    
    cap = f"📩 <b>አዲስ ደረሰኝ</b>\n👤 <b>ከ፦</b> {message.from_user.first_name}\n🆔 <b>ID፦</b> <code>{uid}</code>"
    for adm in ADMIN_IDS:
        try:
            if message.photo: bot.send_photo(adm, message.photo[-1].file_id, caption=cap, reply_markup=markup)
            else: bot.send_message(adm, f"{cap}\n📝 <code>{message.text}</code>", reply_markup=markup)
        except: pass
    bot.reply_to(message, "⏳ <b>ደረሰኝዎ ደርሶኛል!</b> አድሚን እስኪያጸድቅ ይጠብቁ።")

def finalize_app(message, target):
    try:
        amt = int(message.text)
        uid = str(target)
        user = get_user(uid)
        user["wallet"] += amt
        save_data()
        bot.send_message(message.chat.id, f"✅ ለ {uid} {amt} ብር ተጨምሯል።")
        
        active_boards = [bid for bid, info in data["boards"].items() if info["active"]]
        if not active_boards:
            bot.send_message(GROUP_ID, f"🎉 <a href='tg://user?id={uid}'>ተጠቃሚ</a> ክፍያዎ ጸድቋል!")
            return

        if len(active_boards) == 1:
            bid = active_boards
            board = data["boards"][bid]
            markup = types.InlineKeyboardMarkup(row_width=5)
            btns = [types.InlineKeyboardButton(str(i), callback_data=f"pick_{bid}_{i}_{uid}") 
                    for i in range(1, board["max"] + 1) if str(i) not in board["slots"]]
            markup.add(*btns)
            bot.send_message(GROUP_ID, f"✅ <a href='tg://user?id={uid}'>ተጠቃሚ</a> ክፍያ ተረጋግጧል! ሰሌዳ {bid} ላይ ቁጥር ይምረጡ፦", reply_markup=markup)
        else:
            markup = types.InlineKeyboardMarkup()
            for bid in active_boards:
                markup.add(types.InlineKeyboardButton(f"🎰 ሰሌዳ {bid}", callback_data=f"select_{bid}_{uid}"))
            bot.send_message(GROUP_ID, f"✅ <a href='tg://user?id={uid}'>ተጠቃሚ</a> ክፍያ ጸድቋል! ሰሌዳ ይምረጡ፦", reply_markup=markup)
    except: bot.send_message(message.chat.id, "⚠️ ስህተት!")

@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    is_admin = call.from_user.id in ADMIN_IDS
    if call.data.startswith('approve_') and is_admin:
        target = call.data.split('_')
        m = bot.send_message(call.from_user.id, f"💵 ለ ID {target} የሚጨመረውን ብር ይጻፉ፦")
        bot.register_next_step_handler(m, finalize_app, target)
    elif call.data.startswith('decline_') and is_admin:
        target = call.data.split('_')
        m = bot.send_message(call.from_user.id, "❌ ምክንያት ይጻፉ፦")
        bot.register_next_step_handler(m, lambda msg: bot.send_message(target, f"❌ ደረሰኝዎ ውድቅ ሆኗል። ምክንያት፦ {msg.text}"))
    
    elif call.data.startswith('select_'):
        parts = call.data.split('_')
        if len(parts) == 3: # select_bid_uid
            bid, target_uid = parts, parts
            if str(call.from_user.id) != target_uid:
                bot.answer_callback_query(call.id, "⚠️ ምርጫው የእርስዎ አይደለም!", show_alert=True)
                return
            call.data = f"select_{bid}"
        handle_selection(call)

    elif call.data.startswith('pick_'):
        parts = call.data.split('_')
        if len(parts) == 4:
            bid, num, target_uid = parts, parts, parts
            if str(call.from_user.id) != target_uid:
                bot.answer_callback_query(call.id, "⚠️ ለእርስዎ አልተላከም!", show_alert=True)
                return
            finalize_reg_inline(call, bid, num)
        else:
            finalize_reg_inline(call, parts, parts)

    elif call.data.startswith('toggle_') and is_admin:
        bid = call.data.split('_')
        data["boards"][bid]["active"] = not data["boards"][bid]["active"]
        save_data(); bot.answer_callback_query(call.id, "ተቀይሯል!"); edit_board(call)
    
    elif call.data == "admin_manage" and is_admin: manage_menu(call)
    elif call.data.startswith('edit_') and is_admin: edit_board(call)
    elif call.data.startswith('set_') and is_admin:
        _, action, bid = call.data.split('_')
        m = bot.send_message(call.from_user.id, f"አዲስ {action} ይጻፉ፦")
        bot.register_next_step_handler(m, update_board_value, bid, action)
    elif call.data == "admin_manual_reg" and is_admin:
        m = bot.send_message(call.from_user.id, "አጻጻፍ፦ <code>ሰሌዳ-ቁጥር-ስም</code>")
        bot.register_next_step_handler(m, process_manual_reg)
    elif call.data == "admin_reset" and is_admin: reset_menu(call)
    elif call.data.startswith('doreset_') and is_admin:
        bid = call.data.split('_')
        data["boards"][bid]["slots"] = {}; data["pinned_msgs"][bid] = None
        save_data(); update_group_board(bid); bot.answer_callback_query(call.id, "ጸድቷል!")

def handle_selection(call):
    bid = call.data.split('_')
    user = get_user(call.from_user.id)
    board = data["boards"][bid]
    if user["wallet"] < board["price"]:
        bot.answer_callback_query(call.id, "⚠️ በቂ ሂሳብ የሎትም!", show_alert=True); return
    markup = types.InlineKeyboardMarkup(row_width=5)
    btns = [types.InlineKeyboardButton(str(i), callback_data=f"pick_{bid}_{i}") 
            for i in range(1, board["max"] + 1) if str(i) not in board["slots"]]
    markup.add(*btns)
    bot.edit_message_text(f"🎰 ሰሌዳ {bid}\n💰 ቀሪ፦ {user['wallet']} ብር\n\nቁጥር ይምረጡ፦", call.message.chat.id, call.message.message_id, reply_markup=markup)

def finalize_reg_inline(call, bid, num):
    uid = str(call.from_user.id); user = get_user(uid); board = data["boards"][bid]
    if user["wallet"] < board["price"]:
        bot.answer_callback_query(call.id, "⚠️ በቂ ሂሳብ የሎትም!", show_alert=True); return
    user["wallet"] -= board["price"]
    board["slots"][num] = user["name"]
    save_data(); update_group_board(bid); bot.answer_callback_query(call.id, f"✅ ቁጥር {num} ተይዟል!")
    if user["wallet"] >= board["price"]: handle_selection(call)
    else: bot.edit_message_text(f"✅ ተጠናቋል። ቀሪ፦ {user['wallet']} ብር", uid, call.message.message_id)

def manage_menu(call):
    markup = types.InlineKeyboardMarkup()
    for bid in data["boards"]: markup.add(types.InlineKeyboardButton(f"ሰሌዳ {bid}", callback_data=f"edit_{bid}"))
    bot.edit_message_text("ሰሌዳ ይምረጡ፦", call.from_user.id, call.message.message_id, reply_markup=markup)

def edit_board(call):
    bid = call.data.split('_'); b = data["boards"][bid]
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton(f"{'🟢 ክፍት' if b['active'] else '🔴 ዝግ'}", callback_data=f"toggle_{bid}"))
    markup.add(types.InlineKeyboardButton("🎫 ዋጋ", callback_data=f"set_price_{bid}"), types.InlineKeyboardButton("🎁 ሽልማት", callback_data=f"set_prize_{bid}"))
    bot.edit_message_text(f"📊 ሰሌዳ {bid}\n💰 ዋጋ፦ {b['price']}\n🏆 ሽልማት፦ {b['prize']}", call.from_user.id, call.message.message_id, reply_markup=markup)

def update_board_value(message, bid, action):
    try:
        if action == "price": data["boards"][bid]["price"] = int(message.text)
        else: data["boards"][bid]["prize"] = message.text
        save_data(); update_group_board(bid); bot.send_message(message.chat.id, "✅ ተስተካክሏል!")
    except: bot.send_message(message.chat.id, "⚠️ ስህተት!")

def process_manual_reg(message):
    try:
        p = message.text.split('-')
        bid, num, name = p, p, p
        if bid in data["boards"] and num not in data["boards"][bid]["slots"]:
            data["boards"][bid]["slots"][num] = name
            save_data(); update_group_board(bid); bot.send_message(message.chat.id, "✅ ተመዝግቧል!")
        else: bot.send_message(message.chat.id, "⚠️ ስህተት!")
    except: bot.send_message(message.chat.id, "⚠️ አጻጻፍ ስህተት!")

def reset_menu(call):
    markup = types.InlineKeyboardMarkup()
    for bid in data["boards"]: markup.add(types.InlineKeyboardButton(f"Reset {bid}", callback_data=f"doreset_{bid}"))
    bot.send_message(call.from_user.id, "የትኛው ይጽዳ?", reply_markup=markup)

if __name__ == "__main__":
    keep_alive()
    bot.remove_webhook()
    while True:
        try: bot.polling(none_stop=True, interval=1, timeout=20)
        except: time.sleep(5)
