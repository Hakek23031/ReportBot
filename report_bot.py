import telebot
from telebot import types
import sqlite3
import os
import time
from telebot import apihelper
import requests

# 🔥 ФИКС DNS/SSL/ИНТЕРНЕТ
apihelper.REQUESTS_CA_BUNDLE = True
apihelper.SESSION_TIME_TO_LIVE = 60 * 15
requests.adapters.DEFAULT_RETRIES = 3

bot = telebot.TeleBot("8706449969:AAGzBfUCweoVpwpt4gSBkxTvX0f9qSXk6yM")

def init_db():
    if os.path.exists('reports.db'): os.remove('reports.db')
    if os.path.exists('admins.db'): os.remove('admins.db')
    if os.path.exists('updates.db'): os.remove('updates.db')
    if os.path.exists('blocks.db'): os.remove('blocks.db')
    
    # Отчеты
    conn = sqlite3.connect('reports.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, user_name TEXT, text TEXT,
        photo_path TEXT, status TEXT DEFAULT 'новый',
        created TEXT, reject_reason TEXT
    )''')
    conn.commit()
    conn.close()
    
    # Админы
    conn = sqlite3.connect('admins.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE admins (
        user_id INTEGER PRIMARY KEY,
        username TEXT, prefix TEXT DEFAULT 'admin',
        added_by INTEGER, added_date TEXT
    )''')
    c.execute("INSERT OR IGNORE INTO admins VALUES (6144745516, 'owner', '🔥ВЛАДЕЛЕЦ', 6144745516, ?)",
              (time.strftime('%Y-%m-%d %H:%M:%S'),))
    c.execute("INSERT OR IGNORE INTO admins VALUES (6103427979, 'moder', '🔥МОДЕР', 6144745516, ?)",
              (time.strftime('%Y-%m-%d %H:%M:%S'),))
    conn.commit()
    conn.close()
    
    # Блокировка
    conn = sqlite3.connect('blocks.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE blocked_users (
        user_id INTEGER PRIMARY KEY,
        blocked_by INTEGER, block_date TEXT,
        block_reason TEXT
    )''')
    conn.commit()
    conn.close()
    
    # Обновления
    conn = sqlite3.connect('updates.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE updates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER, sender_name TEXT, message TEXT,
        sent_date TEXT
    )''')
    conn.commit()
    conn.close()
    
    os.makedirs("photos", exist_ok=True)
    print("✅ БД создана!")

user_states = {}
reject_states = {}

def get_admin_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.row("📋 Список отчетов", "📊 Статистика")
    markup.row("👥 Список админов", "📖 AHELP")
    markup.row("🔙 Выйти")
    return markup

def is_admin(user_id):
    try:
        conn = sqlite3.connect('admins.db')
        c = conn.cursor()
        c.execute("SELECT prefix FROM admins WHERE user_id=?", (user_id,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None
    except:
        return None

def is_blocked(user_id):
    try:
        conn = sqlite3.connect('blocks.db')
        c = conn.cursor()
        c.execute("SELECT * FROM blocked_users WHERE user_id=?", (user_id,))
        result = c.fetchone()
        conn.close()
        return result is not None
    except:
        return False

def get_all_admins():
    try:
        conn = sqlite3.connect('admins.db')
        c = conn.cursor()
        c.execute("SELECT user_id, username, prefix FROM admins")
        admins = c.fetchall()
        conn.close()
        return admins
    except:
        return [(6144745516, "owner", "🔥ВЛАДЕЛЕЦ"), (6103427979, "moder", "🔥МОДЕР")]

def notify_all_admins(message, exclude_id=None):
    admins = get_all_admins()
    for admin_id, _, _ in admins:
        if admin_id != exclude_id:
            try:
                bot.send_message(admin_id, message, parse_mode='Markdown')
            except:
                pass

def safe_get_report(report_id):
    try:
        conn = sqlite3.connect('reports.db')
        c = conn.cursor()
        c.execute("SELECT user_id, status FROM reports WHERE id=?", (report_id,))
        result = c.fetchone()
        conn.close()
        return result
    except:
        return None

# 🔥 БЛОКИРОВКА
@bot.message_handler(commands=['block'], func=lambda m: is_admin(m.from_user.id))
def block_user(message):
    parts = message.text.split()
    if len(parts) < 2: 
        return bot.send_message(message.chat.id, f"❌ `/block 123456 [причина]`", parse_mode='Markdown', reply_markup=get_admin_menu())
    
    try:
        target_id = int(parts[1].replace('@', ''))
        reason = ' '.join(parts[2:]) if len(parts) > 2 else "Нарушение"
        
        conn = sqlite3.connect('blocks.db')
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO blocked_users VALUES (?, ?, ?, ?)",
                  (target_id, message.from_user.id, time.strftime('%Y-%m-%d %H:%M:%S'), reason))
        conn.commit()
        conn.close()
        
        bot.send_message(message.chat.id, f"🔒 *#{target_id} ЗАБЛОКИРОВАН!*\n📝 *{reason}*", parse_mode='Markdown', reply_markup=get_admin_menu())
        notify_all_admins(f"🔒 `{target_id}` заблокирован: *{reason}*", message.from_user.id)
    except:
        bot.send_message(message.chat.id, f"❌ `/block 123456`", parse_mode='Markdown', reply_markup=get_admin_menu())

@bot.message_handler(commands=['unblock'], func=lambda m: is_admin(m.from_user.id))
def unblock_user(message):
    parts = message.text.split()
    if len(parts) < 2: 
        return bot.send_message(message.chat.id, f"❌ `/unblock 123456`", parse_mode='Markdown', reply_markup=get_admin_menu())
    
    try:
        target_id = int(parts[1].replace('@', ''))
        conn = sqlite3.connect('blocks.db')
        c = conn.cursor()
        c.execute("DELETE FROM blocked_users WHERE user_id=?", (target_id,))
        conn.commit()
        conn.close()
        
        bot.send_message(message.chat.id, f"✅ *#{target_id} РАЗБЛОКИРОВАН!*", parse_mode='Markdown', reply_markup=get_admin_menu())
    except:
        bot.send_message(message.chat.id, f"❌ `/unblock 123456`", parse_mode='Markdown', reply_markup=get_admin_menu())

@bot.message_handler(commands=['blocklist'], func=lambda m: is_admin(m.from_user.id))
def block_list(message):
    conn = sqlite3.connect('blocks.db')
    c = conn.cursor()
    c.execute("SELECT user_id, block_date, block_reason FROM blocked_users ORDER BY block_date DESC LIMIT 10")
    blocked = c.fetchall()
    conn.close()
    
    if not blocked:
        return bot.send_message(message.chat.id, "📭 Блок-лист пуст", reply_markup=get_admin_menu())
    
    text = "🔒 *БЛОК-ЛИСТ*:\n\n"
    for user_id, date, reason in blocked:
        text += f"`{user_id}` — *{reason}*\n"
    bot.send_message(message.chat.id, text, reply_markup=get_admin_menu(), parse_mode='Markdown')

@bot.message_handler(commands=['start'])
def start(message):
    if is_blocked(message.from_user.id):
        bot.send_message(message.chat.id, "🚫 *ВЫ ЗАБЛОКИРОВАНЫ!*")
        return
    
    prefix = is_admin(message.from_user.id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add("📸 Отправить отчет")
    if prefix:
        markup.add("👑 Админ панель")
    bot.send_message(message.chat.id, 
        f"📸 *ReportBot v5.1*\n👤 `{message.from_user.id}`\n🔐 {'👑 ' + prefix if prefix else '👤 Пользователь'}",
        reply_markup=markup, parse_mode='Markdown')

# 🔥 АДМИН МЕНЮ
@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.text in ["👑 Админ панель", "📋 Список отчетов", "📊 Статистика", "👥 Список админов", "📖 AHELP", "🔙 Выйти"])
def admin_menu_handler(message):
    text = message.text
    if text == "👑 Админ панель":
        show_admin_panel(message)
    elif text == "📋 Список отчетов":
        show_reports_list(message)
    elif text == "📊 Статистика":
        show_statistics(message)
    elif text == "👥 Список админов":
        show_admins_list(message)
    elif text == "📖 AHELP":
        show_ahelp(message)
    elif text == "🔙 Выйти":
        start(message)

def show_admin_panel(message):
    prefix = is_admin(message.from_user.id)
    bot.send_message(message.chat.id, f"👑 *{prefix} ПАНЕЛЬ*", reply_markup=get_admin_menu(), parse_mode='Markdown')

def show_ahelp(message):
    prefix = is_admin(message.from_user.id)
    text = f"""📖 *{prefix} AHELP v5.1*

🔹 *🔒 Блокировка:*
🔒 `/block 123456 [причина]`
✅ `/unblock 123456`
📋 `/blocklist`

🔹 *Обновления:*
🔥 `/update Текст`

🔹 *Админы:*
`/admin 123456 [ПРЕФИКС]`
`/deadmin 123456`"""
    bot.send_message(message.chat.id, text, reply_markup=get_admin_menu(), parse_mode='Markdown')

def show_admins_list(message):
    admins = get_all_admins()
    text = "👥 *АДМИНЫ*:\n\n"
    for i, (admin_id, username, prefix) in enumerate(admins, 1):
        text += f"{i}. `{admin_id}` — *{prefix}*\n"
    bot.send_message(message.chat.id, text, reply_markup=get_admin_menu(), parse_mode='Markdown')

def show_reports_list(message):
    conn = sqlite3.connect('reports.db')
    c = conn.cursor()
    c.execute("SELECT id, user_name, status, created FROM reports ORDER BY id DESC LIMIT 15")
    reports = c.fetchall()
    conn.close()
    
    if not reports:
        return bot.send_message(message.chat.id, "📭 Нет отчетов", reply_markup=get_admin_menu())
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    text = "📋 *ОТЧЕТЫ*:\n\n"
    for report in reports:
        status = "🆕" if report[2] == 'новый' else "✅" if report[2] == 'принят' else "❌"
        text += f"{status} *#{report[0]}* {report[1]}\n"
        markup.add(types.InlineKeyboardButton(f"👁️ #{report[0]}", callback_data=f"view_{report[0]}"))
    
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

def show_statistics(message):
    conn = sqlite3.connect('reports.db')
    c = conn.cursor()
    c.execute("SELECT status, COUNT(*) FROM reports GROUP BY status")
    stats = dict(c.fetchall() or [])
    conn.close()
    total = sum(stats.values())
    text = f"""📊 *СТАТИСТИКА*
Всего: `{total}`
🆕 Новых: `{stats.get('новый', 0)}`
✅ Принято: `{stats.get('принят', 0)}`
❌ Отклонено: `{stats.get('отклонен', 0)}`"""
    bot.send_message(message.chat.id, text, reply_markup=get_admin_menu(), parse_mode='Markdown')

# ОТЧЕТЫ
@bot.message_handler(func=lambda m: m.text == "📸 Отправить отчет" and not is_blocked(m.from_user.id))
def send_report(message):
    user_states[message.from_user.id] = {'step': 'wait_text'}
    bot.send_message(message.chat.id, "📝 Напишите описание проблемы:")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    
    if is_blocked(user_id):
        bot.send_message(message.chat.id, "🚫 *ВЫ ЗАБЛОКИРОВАНЫ!*")
        return
    
    if user_id in reject_states:
        report_id = reject_states[user_id]['report_id']
        return process_reject_reason(message, report_id)
    
    if user_id in user_states and user_states[user_id].get('step') == 'wait_text':
        user_states[user_id]['text'] = message.text
        user_states[user_id]['step'] = 'wait_photo'
        return bot.send_message(message.chat.id, "📸 Отправьте скриншот:")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if is_blocked(message.from_user.id):
        bot.send_message(message.chat.id, "🚫 *ВЫ ЗАБЛОКИРОВАНЫ!*")
        return
        
    user_id = message.from_user.id
    if user_id in user_states and user_states[user_id].get('step') == 'wait_photo':
        save_report(message)
        user_states.pop(user_id, None)

def save_report(message):
    try:
        user_id = message.from_user.id
        text = user_states[user_id]['text']
        file_info = bot.get_file(message.photo[-1].file_id)
        timestamp = int(time.time())
        photo_path = f"photos/r{user_id}_{timestamp}.jpg"
        
        downloaded_file = bot.download_file(file_info.file_path)
        with open(photo_path, 'wb') as f:
            f.write(downloaded_file)
        
        conn = sqlite3.connect('reports.db')
        c = conn.cursor()
        c.execute("INSERT INTO reports (user_id, user_name, text, photo_path, created) VALUES (?, ?, ?, ?, ?)",
                  (user_id, message.from_user.first_name or "User", text, photo_path, time.strftime('%Y-%m-%d %H:%M:%S')))
        report_id = c.lastrowid
        conn.commit()
        conn.close()
        
        bot.send_message(message.chat.id, f"✅ *Отчет #{report_id} отправлен!*", parse_mode='Markdown')
        notify_all_admins(f"🆕 *НОВЫЙ ОТЧЕТ #{report_id}*\n\n👤 {message.from_user.first_name}\n📝 {text}")
    except Exception as e:
        print(f"Ошибка: {e}")

def process_reject_reason(message, report_id):
    reason = message.text
    result = safe_get_report(report_id)
    
    if result and result[1] == 'новый':
        conn = sqlite3.connect('reports.db')
        c = conn.cursor()
        c.execute("UPDATE reports SET status='отклонен', reject_reason=? WHERE id=?", (reason, report_id))
        conn.commit()
        conn.close()
        
        bot.send_message(message.chat.id, f"✅ *#{report_id}* отклонен!", parse_mode='Markdown', reply_markup=get_admin_menu())
    reject_states.pop(message.from_user.id, None)

# 🔥 CALLBACK ДЛЯ КНОПОК
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    data = call.data
    
    if data.startswith('view_'):
        report_id = int(data.split('_')[1])
        conn = sqlite3.connect('reports.db')
        c = conn.cursor()
        c.execute("SELECT * FROM reports WHERE id=?", (report_id,))
        report = c.fetchone()
        conn.close()
        
        if report:
            status_emoji = "🆕" if report[5] == 'новый' else "✅" if report[5] == 'принят' else "❌"
            text = f"📊 *ОТЧЕТ #{report[0]}*\n\n👤 {report[2]}\n📝 {report[3]}\n📅 {report[6][:16]}\n📊 *{status_emoji} {report[5]}*"
            
            try:
                with open(report[4], 'rb') as photo:
                    bot.send_photo(call.message.chat.id, photo, text, parse_mode='Markdown')
            except:
                bot.send_message(call.message.chat.id, text + "\n❌ Фото не найдено", parse_mode='Markdown')
        
        bot.answer_callback_query(call.id, f"👁️ #{report_id}")

if __name__ == "__main__":
    while True:
        try:
            print("🚀 ReportBot v5.1 запущен!")
            init_db()
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(5)
