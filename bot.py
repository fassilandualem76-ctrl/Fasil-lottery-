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
def home(): return "Damene & Fasil Lotto System is Active!"

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

# የክፍያ መረጃዎች (Shift System)
PAYMENTS = {
    "me": "👉ንግድ ባንክ 1000584461757 ፋሲል\n👉 ቴሌ ብር 0951381351 ፋሲል",
    "assistant": "👉ንግድ ባንክ 1000718691323 ዳመነ\n👉 ቴሌ ብር 0973416038 ዳመነ"
}

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
redis = Redis(url="https://sunny-ferret-79578.upstash.io", token="gQAAAAAAATbaAAIncDE4MTQ2MThjMjVjYjI0YzU5OGQ0MjMzZGI0MGIwZTkwNXAxNzk1Nzg")

# --- 3. ዳታቤዝ አያያዝ ---
data = {
    "users": {},
    "current_shift": "me",
    "boards": {
        "1": {"max": 100, "price": 400, "prize": "1ኛ🟢21,000 | 2ኛ🟡7,000 | 3ኛ🔴3,000", "slots": {}}
    },
    "pinned_msgs": {"1": None}
}

def save_data():
    try: redis.set("fasil_lotto_db", json.dumps(data))
    except: pass

def load_data():
    global data
    try:
        raw = redis.get("fasil_lotto_db")
        if raw: data = json.loads(raw)
    except: pass

load_data()

# --- 4. የሰሌዳ ዲዛይን (የውቤ/ዳመነና ፋሲል ስታይል) ---
def update_group_board(b_id):
    board = data["boards"][b_id]
    shift_key = data.get("current_shift", "me")
    pay_info = PAYMENTS[shift_key]
    
    text = f"🇪🇹<b>ዳመነ እና ፋሲል 💸💰</b>🇪🇹🇪🇹\n"
    text += f"              <b>በ400 ብር</b>\n"
    text += f"              👇👇👇👇👇\n"
    text += f"      <b>{board['prize']}</b>\n\n"
    text += f"☎️⏰ለ ውድ ዳመነ እና ፋሲል 💸💰 ቤተሰብ\nመልካም እድል🏆 USE IT OR LOSE IT\n\n"
    text += f"      <b>ገቢ መስገቢያ አማራጮች</b>\n{pay_info}\n\n"
    
    # 1-100 ዝርዝር
    for i in range(1, board["max"] + 1):
        s_i = str(i)
        if s_i in board["slots"]:
            text += f"{s_i}👉<b>{board['slots'][s_i]}✅🏆🙏</b>\n"
        else:
            text += f"{s_i}👉⬜️⬜️⬜️⬜️\n"
            
    text += f"\n<b>ዳመነ እና ፋሲል 💸💰 online መዝናኛ ቤተሰብ</b>\n"
    text += f"መልካም ቀን🏆መልካም ጤና🏆 መልካም እድል🏆🏆🏆\n☎️ ስልክ፦ 0973416038"

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

# --- 5. የአድሚን ትዕዛዞች ---

@bot.message_handler(commands=['shift'])
def toggle_shift(message):
    if message.from_user.id in ADMIN_IDS:
        data["current_shift"] = "assistant" if data["current_shift"] == "me" else "me"
        save_data()
        update_group_board("1")
        bot.reply_to(message, f"🔄 ፈረቃ ተቀይሯል! ተረኛ፦ {'ዳመነ' if data['current_shift'] == 'assistant' else 'ፋሲል'}")

# በአካል መመዝገቢያ (1-15-አበበ)
@bot.message_handler(func=lambda m: "-" in m.text and m.from_user.id in ADMIN_IDS)
def manual_entry(message):
    try:
        bid, num, name = message.text.split("-")
        if bid in data["boards"]:
            data["boards"][bid]["slots"][num] = name[:10]
            save_data()
            update_group_board(bid)
            bot.delete_message(message.chat.id, message.message_id)
    except: pass

# ደረሰኝ ማጽደቅ (Reply ok 400)
@bot.message_handler(func=lambda m: m.chat.id == GROUP_ID and m.reply_to_message and m.from_user.id in ADMIN_IDS)
def approve_receipt(message):
    text = message.text.lower()
    if "ok" in text or "እሺ" in text:
        try:
            amount = int(''.join(filter(str.isdigit, text)))
            target_user = message.reply_to_message.from_user
            uid = str(target_user.id)
            
            if uid not in data["users"]:
                data["users"][uid] = {"name": target_user.first_name[:10], "wallet": 0}
            
            data["users"][uid]["wallet"] += amount
            save_data()
            
            bot.reply_to(message.reply_to_message, f"✅ ተረጋግጦልሃል! ደረሰኝ ደርሶኛል።")
            show_auto_buttons(message.chat.id, uid)
        except: pass

def show_auto_buttons(chat_id, uid):
    bid = "1"
    board = data["boards"][bid]
    user = data["users"][uid]
    
    if user["wallet"] < board["price"]: return

    markup = types.InlineKeyboardMarkup(row_width=5)
    btns = []
    for i in range(1, board["max"] + 1):
        if str(i) not in board["slots"]:
            btns.append(types.InlineKeyboardButton(str(i), callback_data=f"pick_{uid}_{bid}_{i}"))
    
    markup.add(*btns[:60]) # ለመጀመሪያ ጊዜ 60 ባተን ብቻ ማሳየት (ለፍጥነት)
    bot.send_message(chat_id, f"🎫 <a href='tg://user?id={uid}'>{user['name']}</a> ቁጥር ምረጥ፦", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('pick_'))
def handle_picking(call):
    _, owner_id, bid, num = call.data.split('_')
    
    if str(call.from_user.id) != owner_id:
        bot.answer_callback_query(call.id, "❌ ምርጫው የአንተ አይደለም!", show_alert=True)
        return

    uid = str(call.from_user.id)
    board = data["boards"][bid]
    user = data["users"][uid]

    if user["wallet"] < board["price"]:
        bot.edit_message_text("💰 ብር አልቆብሃል።", call.message.chat.id, call.message.message_id)
        return

    # ምዝገባ
    data["users"][uid]["wallet"] -= board["price"]
    board["slots"][num] = user["name"]
    save_data()
    update_group_board(bid)
    
    bot.answer_callback_query(call.id, f"✅ ቁጥር {num} ተይዟል")

    # ብር ከቀረው ባተኑ እንዲቀጥል፣ ካለቀ እንዲጠፋ
    if data["users"][uid]["wallet"] >= board["price"]:
        markup = types.InlineKeyboardMarkup(row_width=5)
        btns = [types.InlineKeyboardButton(str(i), callback_data=f"pick_{uid}_{bid}_{i}") 
                for i in range(1, board["max"] + 1) if str(i) not in board["slots"]]
        markup.add(*btns[:60])
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)
    else:
        bot.delete_message(call.message.chat.id, call.message.message_id)

if __name__ == "__main__":
    save_data()
    keep_alive()
    bot.remove_webhook()
    while True:
        try: bot.polling(none_stop=True, interval=0, timeout=20)
        except: time.sleep(5)
