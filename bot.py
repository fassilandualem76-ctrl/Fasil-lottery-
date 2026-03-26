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
    "me": {"name": "ፋሲል", "tele": "0951381356", "cbe": "1000584461757"},
    "assistant": {"name": "ዳመነ", "tele": "0973416038", "cbe": "1000718691323"}
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
        with open(DB_FILE, "w") as f: json.dump(data, f)
    except: pass

def load_data():
    global data
    try:
        raw = redis.get("fasil_lotto_db")
        if raw: data = json.loads(raw)
    except: pass

load_data()

def get_user(uid, name="ተጫዋች"):
    uid = str(uid)
    if uid not in data["users"]: data["users"][uid] = {"name": name, "wallet": 0}
    return data["users"][uid]

# --- 4. የሰሌዳ ዲዛይን (Wube Style) ---
def update_group_board(b_id):
    board = data["boards"][b_id]
    shift = data["current_shift"]
    pay = PAYMENTS[shift]
    other = "assistant" if shift == "me" else "me"
    
    text = f"🇪🇹 <b>{pay['name']} እና {PAYMENTS[other]['name']} 💸💰 Online መዝናኛ</b> 🇪🇹\n"
    text += f"          <b>በ {board['price']} ብር ብቻ</b>\n"
    text += f"      👇👇👇👇👇👇👇👇👇\n"
    text += f"🏆 <b>ሽልማት፦ {board['prize']}</b>\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"🏦 <b>ገቢ መስገቢያ አማራጮች ({pay['name']})</b>\n\n"
    text += f"👉 ቴሌ ብር፦ <code>{pay['tele']}</code>\n"
    text += f"👉 ንግድ ባንክ፦ <code>{pay['cbe']}</code>\n"
    text += f"━━━━━━━━━━━━━━━━━━━━━\n\n"

    for i in range(1, board["max"] + 1):
        num = str(i)
        text += f"{i}👉 <b>{board['slots'][num]}</b> ✅🏆🙏\n" if num in board["slots"] else f"{i}👉 ❤❤❤❤❤\n"

    text += f"\n━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"🏆 <b>መልካም እድል! USE IT OR LOSE IT</b>\n"
    text += f"🤖 ለመጫወት ደረሰኝ እዚህ ግሩፕ ላይ ይላኩ"

    try:
        if data["pinned_msgs"].get(b_id):
            bot.edit_message_text(text[:4000], GROUP_ID, data["pinned_msgs"][b_id])
        else:
            m = bot.send_message(GROUP_ID, text[:4000]); bot.pin_chat_message(GROUP_ID, m.message_id)
            data["pinned_msgs"][b_id] = m.message_id; save_data()
    except: pass

# --- 5. Handlers & Admin ---
@bot.message_handler(commands=['start'])
def welcome(message):
    uid = str(message.chat.id); user = get_user(uid, message.from_user.first_name)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎮 ሰሌዳ ምረጥ", "👤 ፕሮፋይል")
    if message.chat.id in ADMIN_IDS: markup.add("⚙️ Admin Settings")
    bot.send_message(uid, f"👋 ሰላም {user['name']}! ሂሳብዎ፦ {user['wallet']} ብር", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "⚙️ Admin Settings" and m.from_user.id in ADMIN_IDS)
def admin_panel(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🔍 አሸናፊ ፈልግ", callback_data="admin_lookup"),
        types.InlineKeyboardButton("⚙️ ሰሌዳ ክፈት/ዝጋ", callback_data="admin_manage"),
        types.InlineKeyboardButton("🎁 ሽልማት ቀይር", callback_data="admin_set_prize"),
        types.InlineKeyboardButton("🔄 ሰሌዳ አፅዳ (Reset)", callback_data="admin_reset"),
        types.InlineKeyboardButton("🔄 ፈረቃ ቀይር (Shift)", callback_data="admin_shift")
    )
    bot.send_message(message.chat.id, "🛠 <b>የአድሚን መቆጣጠሪያ</b>", reply_markup=markup)

@bot.message_handler(content_types=['photo', 'text'])
def handle_receipts(message):
    if message.chat.id == GROUP_ID:
        if message.text and "-" in message.text and message.from_user.id in ADMIN_IDS:
            try:
                parts = message.text.split('-')
                bid, num, name = parts, parts, parts
                if bid in data["boards"]:
                    data["boards"][bid]["slots"][num] = name[:5]
                    save_data(); update_group_board(bid)
                    bot.reply_to(message, f"✅ ሰሌዳ {bid} ቁጥር {num} ተመዝግቧል!")
            except: pass
        return

    uid = str(message.chat.id)
    if message.text in ["🎮 ሰሌዳ ምረጥ", "👤 ፕሮፋይል", "⚙️ Admin Settings"]: return
    
    markup = types.InlineKeyboardMarkup().row(
        types.InlineKeyboardButton("✅ አፅድቅ", callback_data=f"app_{uid}"), 
        types.InlineKeyboardButton("❌ ውድቅ", callback_data=f"dec_{uid}")
    )
    for adm in ADMIN_IDS:
        try:
            if message.photo: bot.send_photo(adm, message.photo[-1].file_id, caption=f"📩 ደረሰኝ ከ {message.from_user.first_name}\nID: <code>{uid}</code>", reply_markup=markup)
            else: bot.send_message(adm, f"📩 መልዕክት ከ {message.from_user.first_name}:\n<code>{message.text}</code>", reply_markup=markup)
        except: pass

@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    is_admin = call.from_user.id in ADMIN_IDS
    if call.data.startswith('app_') and is_admin:
        m = bot.send_message(call.from_user.id, f"💵 ለ ID {call.data.split('_')} የሚጨመረውን ብር ይጻፉ፦")
        bot.register_next_step_handler(m, finalize_app, call.data.split('_'))
    
    elif call.data == "admin_lookup" and is_admin:
        m = bot.send_message(call.from_user.id, "አሸናፊ ለመፈለግ ሰሌዳ እና ቁጥር ይጻፉ (ለምሳሌ: 1-15)፦")
        bot.register_next_step_handler(m, process_lookup)

    elif call.data == "admin_manage" and is_admin:
        markup = types.InlineKeyboardMarkup()
        for bid, binfo in data["boards"].items():
            txt = f"ሰሌዳ {bid} {'🔴 ዝጋ' if binfo['active'] else '🟢 ክፈት'}"
            markup.add(types.InlineKeyboardButton(txt, callback_data=f"toggle_{bid}"))
        bot.edit_message_text("የሚቀየር ሰሌዳ ይምረጡ፦", call.from_user.id, call.message.message_id, reply_markup=markup)

    elif call.data.startswith('toggle_') and is_admin:
        bid = call.data.split('_')
        data["boards"][bid]["active"] = not data["boards"][bid]["active"]
        save_data(); bot.answer_callback_query(call.id, "ተቀይሯል!"); admin_panel(call.message)

    elif call.data == "admin_reset" and is_admin:
        markup = types.InlineKeyboardMarkup()
        for bid in data["boards"]: markup.add(types.InlineKeyboardButton(f"Reset {bid}", callback_data=f"doreset_{bid}"))
        bot.edit_message_text("የትኛው ሰሌዳ ይጽዳ?", call.from_user.id, call.message.message_id, reply_markup=markup)

    elif call.data.startswith('doreset_') and is_admin:
        bid = call.data.split('_')
        data["boards"][bid]["slots"] = {}; data["pinned_msgs"][bid] = None
        save_data(); update_group_board(bid); bot.answer_callback_query(call.id, "ጸድቷል!")

    elif call.data == "admin_shift" and is_admin:
        data["current_shift"] = "assistant" if data["current_shift"] == "me" else "me"
        save_data(); bot.answer_callback_query(call.id, f"ተረኛ፦ {PAYMENTS[data['current_shift']]['name']}")
        bot.send_message(call.from_user.id, f"🔄 ፈረቃ ተቀይሯል። አሁን ተረኛው፦ {PAYMENTS[data['current_shift']]['name']} ነው")

    elif call.data == "admin_set_prize" and is_admin:
        markup = types.InlineKeyboardMarkup()
        for bid in data["boards"]: markup.add(types.InlineKeyboardButton(f"ሰሌዳ {bid} ሽልማት", callback_data=f"setpriz_{bid}"))
        bot.edit_message_text("ሽልማት የሚቀየርበትን ሰሌዳ ይምረጡ፦", call.from_user.id, call.message.message_id, reply_markup=markup)

    elif call.data.startswith('setpriz_') and is_admin:
        bid = call.data.split('_')
        m = bot.send_message(call.from_user.id, f"ለሰሌዳ {bid} አዲሱን ሽልማት ይጻፉ፦\n(ለምሳሌ፦ 1ኛ 300, 2ኛ 100)")
        bot.register_next_step_handler(m, save_new_prize, bid)

    elif call.data.startswith('pick_'):
        parts = call.data.split('_')
        if len(parts) < 4: return
        _, bid, num, target_uid = parts, parts, parts, parts
        if str(call.from_user.id) != target_uid:
            bot.answer_callback_query(call.id, "⚠️ ይህ የእርስዎ ምርጫ አይደለም!", show_alert=True); return
        finalize_reg(call, bid, num, target_uid)

def finalize_app(message, target_uid):
    try:
        amt = int(message.text); user = get_user(target_uid)
        user["wallet"] += amt
        try:
            c = bot.get_chat(target_uid)
            user["name"] = (c.first_name[:5]) if (c and c.first_name) else "ተጫዋች"
        except: pass
        save_data(); bot.send_message(target_uid, f"✅ {amt} ብር ተጨምሯል!")
        
        active = [b for b, info in data["boards"].items() if info["active"]]
        if len(active) == 1: send_nums(target_uid, active)
        else:
            markup = types.InlineKeyboardMarkup()
            for b in active: markup.add(types.InlineKeyboardButton(f"🎰 ሰሌዳ {b}", callback_data=f"pick_select_{b}_{target_uid}"))
            bot.send_message(GROUP_ID, f"🔔 <a href='tg://user?id={target_uid}'>ተጫዋች</a> ሰሌዳ ይምረጡ፦", reply_markup=markup)
    except: bot.send_message(message.chat.id, "⚠️ ቁጥር ብቻ ያስገቡ።")

def send_nums(uid, bid):
    board = data["boards"][bid]; user = get_user(uid)
    markup = types.InlineKeyboardMarkup(row_width=5)
    btns = [types.InlineKeyboardButton(str(i), callback_data=f"pick_{bid}_{i}_{uid}") for i in range(1, board["max"]+1) if str(i) not in board["slots"]]
    markup.add(*btns)
    bot.send_message(GROUP_ID, f"🎰 <a href='tg://user?id={uid}'>ተጫዋች</a> ሰሌዳ {bid} ቁጥር ይምረጡ (ቀሪ፦ {user['wallet']} ብር)፦", reply_markup=markup)

def finalize_reg(call, bid, num, uid):
    user = get_user(uid); board = data["boards"][bid]
    if user["wallet"] < board["price"]:
        bot.answer_callback_query(call.id, "⚠️ በቂ ሂሳብ የሎትም!"); bot.delete_message(GROUP_ID, call.message.message_id); return
    
    user["wallet"] -= board["price"]; board["slots"][num] = user["name"]
    save_data(); update_group_board(bid); bot.answer_callback_query(call.id, f"✅ ቁጥር {num} ተመርጧል!")
    
    if user["wallet"] >= board["price"]:
        markup = types.InlineKeyboardMarkup(row_width=5)
        btns = [types.InlineKeyboardButton(str(i), callback_data=f"pick_{bid}_{i}_{uid}") for i in range(1, board["max"]+1) if str(i) not in board["slots"]]
        markup.add(*btns); bot.edit_message_reply_markup(GROUP_ID, call.message.message_id, reply_markup=markup)
    else:
        bot.delete_message(GROUP_ID, call.message.message_id)
        bot.send_message(GROUP_ID, f"✅ <a href='tg://user?id={uid}'>ተጫዋች</a> ምዝገባዎ ተጠናቋል።")

def process_lookup(message):
    try:
        bid, num = message.text.split('-')
        winner = data["boards"][bid]["slots"].get(num, "አልተያዘም")
        bot.send_message(message.chat.id, f"🔎 <b>ውጤት፦</b>\n🎰 ሰሌዳ {bid}\n🎫 ቁጥር {num}\n👤 ስም፦ {winner}")
    except: bot.send_message(message.chat.id, "⚠️ ስህተት (1-15)")

def save_new_prize(message, bid):
    data["boards"][bid]["prize"] = message.text
    save_data(); update_group_board(bid)
    bot.send_message(message.chat.id, f"✅ የሰሌዳ {bid} ሽልማት ተቀይሯል!")

if __name__ == "__main__":
    keep_alive()
    bot.remove_webhook()
    bot.polling(none_stop=True)
