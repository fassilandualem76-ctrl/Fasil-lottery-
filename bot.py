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
def home(): return "Fasil & Damene Group System is Active!"

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
ADMIN_IDS = [MY_ID, ASSISTANT_ID]

PAYMENTS = {
    "ፋሲል": {
        "text": "👉 ንግድ ባንክ 1000584461757\n👉 ቴሌ ብር 0951381356",
        "tele": "0951381356", "cbe": "1000584461757"
    },
    "ዳመነ": {
        "text": "👉 ንግድ ባንክ 1000718691323\n👉 ቴሌ ብር 0973416038",
        "tele": "0973416038", "cbe": "1000718691323"
    }
}

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
redis = Redis(url="https://sunny-ferret-79578.upstash.io", token="gQAAAAAAATbaAAIncDE4MTQ2MThjMjVjYjI0YzU5OGQ0MjMzZGI0MGIwZTkwNXAxNzk1Nzg")

# --- 3. ዳታቤዝ ---
data = {"users": {}, "current_shift": "ፋሲል", "boards": {"1": {"max": 100, "price": 400, "prize": "1ኛ 21,000, 2ኛ 7,000, 3ኛ 3,000", "slots": {}}}, "pinned_msgs": {"1": None}}

def save_data(): redis.set("fasil_lotto_db", json.dumps(data))
def load_data():
    global data
    raw = redis.get("fasil_lotto_db")
    if raw: data = json.loads(raw)
load_data()

# --- 4. የሰሌዳ ዲዛይን ---
def update_group_board(b_id):
    board = data["boards"].get(b_id)
    shift = data.get("current_shift", "ፋሲል")
    acc_info = PAYMENTS[shift]["text"]
    text = f"<b>🇪🇹 {data['current_shift']} እና ፋሲል መዝናኛ 🇪🇹</b>\n              <b>በ{board['price']} ብር</b>\n              👇👇👇👇👇\n      <b>{board['prize']}</b>\n\n☎️ 0910984771\n\n      <b>ገቢ መስገቢያ አማራጮች</b>\n{acc_info}\n\n"
    for i in range(1, board["max"] + 1):
        s_i = str(i)
        if s_i in board["slots"]: text += f"<b>{s_i}👉{board['slots'][s_i]}✅🏆🙏</b>\n"
        else: text += f"<b>{s_i}👉⬜️⬜️⬜️⬜️</b>\n"
    try:
        if data["pinned_msgs"].get(b_id): bot.edit_message_text(text, GROUP_ID, data["pinned_msgs"][b_id])
        else:
            m = bot.send_message(GROUP_ID, text); bot.pin_chat_message(GROUP_ID, m.message_id)
            data["pinned_msgs"][b_id] = m.message_id; save_data()
    except: pass

# --- 5. አድሚን አፕሩቭ ሲያደርግ (እዛው ግሩፕ ላይ) ---
@bot.message_handler(func=lambda m: m.chat.id == GROUP_ID and m.reply_to_message and m.from_user.id in ADMIN_IDS)
def admin_action(message):
    text = message.text.lower()
    if "ok" in text or "እሺ" in text:
        try:
            amt = int(''.join(filter(str.isdigit, text)))
            target_user = message.reply_to_message.from_user
            uid = str(target_user.id)
            if uid not in data["users"]: data["users"][uid] = {"name": target_user.first_name[:5], "wallet": 0}
            data["users"][uid]["wallet"] += amt
            save_data()
            
            # ቁጥር መምረጫ ባተን ለከፋዩ ብቻ እንዲታይ
            show_pick_buttons(message.chat.id, uid, amt)
        except: bot.reply_to(message, "⚠️ እባክህ ብሩን በትክክል ጻፍ (ለምሳሌ: ok 400)")

def show_pick_buttons(chat_id, uid, amt):
    bid = "1"
    board = data["boards"][bid]
    markup = types.InlineKeyboardMarkup(row_width=5)
    btns = [types.InlineKeyboardButton(str(i), callback_data=f"p_{uid}_{bid}_{i}") for i in range(1, board["max"] + 1) if str(i) not in board["slots"]]
    markup.add(*btns)
    bot.send_message(chat_id, f"✅ ደረሰኝ ጸድቋል! <a href='tg://user?id={uid}'>{data['users'][uid]['name']}</a> እባክህ {amt} ብር የሚያስመርጥህን ቁጥር ምረጥ፦", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('p_'))
def handle_selection(call):
    _, owner_id, bid, num = call.data.split('_')
    if str(call.from_user.id) != owner_id:
        bot.answer_callback_query(call.id, "❌ ይህ ምርጫ የአንተ አይደለም!", show_alert=True); return

    uid = str(call.from_user.id)
    board = data["boards"][bid]
    if data["users"][uid]["wallet"] < board["price"]:
        bot.answer_callback_query(call.id, "⚠️ ቀሪ ሂሳብ የለዎትም!"); bot.delete_message(call.message.chat.id, call.message.message_id); return

    data["users"][uid]["wallet"] -= board["price"]
    board["slots"][num] = data["users"][uid]["name"]
    save_data(); update_group_board(bid)
    
    if data["users"][uid]["wallet"] >= board["price"]:
        # ገና ብር ካለው ባተኑን አድሶ ያሳየዋል
        new_markup = types.InlineKeyboardMarkup(row_width=5)
        btns = [types.InlineKeyboardButton(str(i), callback_data=f"p_{uid}_{bid}_{i}") for i in range(1, board["max"] + 1) if str(i) not in board["slots"]]
        new_markup.add(*btns)
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=new_markup)
    else:
        bot.edit_message_text(f"✅ ምዝገባ ተጠናቋል! መልካም እድል {data['users'][uid]['name']}!", call.message.chat.id, call.message.message_id)

# --- Manual Entry & Shift ---
@bot.message_handler(commands=['shift'])
def shift_cmd(message):
    if message.from_user.id in ADMIN_IDS:
        data["current_shift"] = "ዳመነ" if data["current_shift"] == "ፋሲል" else "ፋሲል"
        save_data(); update_group_board("1"); bot.reply_to(message, f"🔄 ተረኛ፦ {data['current_shift']}")

@bot.message_handler(func=lambda m: "-" in m.text and m.from_user.id in ADMIN_IDS)
def manual_entry(message):
    try:
        bid, num, name = message.text.split("-")
        data["boards"][bid]["slots"][num] = name[:5]
        save_data(); update_group_board(bid); bot.reply_to(message, "✅ ተመዝግቧል")
    except: pass

if __name__ == "__main__":
    keep_alive()
    bot.remove_webhook()
    bot.polling(none_stop=True)
