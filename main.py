import asyncio
import sqlite3
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- НАСТРОЙКИ ---
TOKEN = "8274120492:AAFhqqzbSdNbCUYrHkPWYSmYX8nQq2VWjDs"
DAILY_REWARD = 100
BASE_COOLDOWN = 3600  # Секунд между карточками

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- РАБОТА С БАЗОЙ ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('cards_game.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            points INTEGER DEFAULT 0,
            cooldown_lvl INTEGER DEFAULT 0,
            luck_lvl INTEGER DEFAULT 0,
            last_card_time TEXT,
            last_daily_date TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('cards_game.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute('INSERT INTO users (user_id) VALUES (?)', (user_id,))
        conn.commit()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
    conn.close()
    return {
        "id": user[0], "points": user[1], "cooldown_lvl": user[2],
        "luck_lvl": user[3], "last_card": user[4], "last_daily": user[5]
    }

def update_user(user_id, key, value):
    conn = sqlite3.connect('cards_game.db')
    cursor = conn.cursor()
    cursor.execute(f'UPDATE users SET {key} = ? WHERE user_id = ?', (value, user_id))
    conn.commit()
    conn.close()

# --- ОБРАБОТЧИКИ КОМАНД ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    get_user(message.from_user.id)
    builder = InlineKeyboardBuilder()
    bot_info = await bot.get_me()
    builder.row(types.InlineKeyboardButton(
        text="➕ Добавить в группу", 
        url=f"https://t.me/{bot_info.username}?startgroup=true")
    )
    await message.answer(
        "👋 Привет! Я бот для игры с карточками. 🐱\n\n"
        "🎮 **Как играть:**\n"
        "• Пиши 'карточка' — получи кота и очки\n"
        "• Пиши 'профиль' — твоя стата\n"
        "• Пиши 'магазин' — прокачка\n"
        "• Пиши 'ежедневка' — бонус 100 очков\n"
        "• Пиши 'топ' — лучшие игроки\n\n"
        "Добавь меня в группу и начинай играть! ✨",
        reply_markup=builder.as_markup()
    )

@dp.message(F.text.lower() == "профиль")
async def cmd_profile(message: types.Message):
    user = get_user(message.from_user.id)
    cd = max(500, BASE_COOLDOWN - user['cooldown_lvl'] * 500)
    text = (
        f"👤 **Профиль: {message.from_user.first_name}**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 Очки: **{user['points']}**\n"
        f"⚡ Уровень КД: {user['cooldown_lvl']} (пауза {cd}с)\n"
        f"🍀 Уровень удачи: {user['luck_lvl']}\n"
        f"━━━━━━━━━━━━━━━━━━"
    )
    await message.answer(text)

@dp.message(F.text.lower() == "ежедневка")
async def daily_bonus(message: types.Message):
    user = get_user(message.from_user.id)
    today = datetime.now().strftime("%Y-%m-%d")
    if user['last_daily'] == today:
        await message.reply("🎁 Ты уже забирал награду сегодня! 💤")
    else:
        update_user(user['id'], "points", user['points'] + DAILY_REWARD)
        update_user(user['id'], "last_daily_date", today)
        await message.reply(f"💰 Ежедневная награда **+{DAILY_REWARD}** получена! ✨")

@dp.message(F.text.lower() == "карточка")
async def give_card(message: types.Message):
    user = get_user(message.from_user.id)
    now = datetime.now()
    cd_sec = max(10, BASE_COOLDOWN - user['cooldown_lvl'] * 10)
    
    if user['last_card']:
        last_time = datetime.strptime(user['last_card'], "%Y-%m-%d %H:%M:%S")
        if now < last_time + timedelta(seconds=cd_sec):
            wait = int((last_time + timedelta(seconds=cd_sec) - now).total_seconds())
            await message.reply(f"⏳ Подожди {wait} сек.!")
            return

    # Шансы (удача немного влияет на легендарки)
    luck = user['luck_lvl']
    weights = [60, 20, 10, 5, 4, 1 + luck] 
    rarities = ["Обычная ⚪", "Редкая 🟢", "Сверхредкая 🔵", "Эпическая 🟣", "Мифическая 🔴", "Легендарная 🟡"]
    res = random.choices(rarities, weights=weights[:6])[0]
    
    reward = 50 + (luck * 10)
    update_user(user['id'], "points", user['points'] + reward)
    update_user(user['id'], "last_card_time", now.strftime("%Y-%m-%d %H:%M:%S"))
    
    await message.reply(f"🐱 Твоя карточка: **{res}**\n💰 Награда: +{reward} (Всего: {user['points'] + reward})")

@dp.message(F.text.lower() == "магазин")
async def shop(message: types.Message):
    user = get_user(message.from_user.id)
    p1 = (user['cooldown_lvl'] + 1) * 200
    p2 = (user['luck_lvl'] + 1) * 300
    await message.answer(
        f"🏪 **МАГАЗИН** (Твой баланс: {user['points']})\n\n"
        f"1️⃣ **Быстрые лапки** (Ур. {user['cooldown_lvl']})\n"
        f"   -10 сек. перезарядки. Цена: {p1}\n"
        f"2️⃣ **Кот удачи** (Ур. {user['luck_lvl']})\n"
        f"   Выше шанс и награда. Цена: {p2}\n\n"
        f"Пиши 'купить 1' или 'купить 2'"
    )

@dp.message(F.text.lower().startswith("купить"))
async def buy_upgrade(message: types.Message):
    user = get_user(message.from_user.id)
    choice = message.text.split()[-1]
    
    if choice == "1":
        cost = (user['cooldown_lvl'] + 1) * 200
        if user['points'] >= cost and user['cooldown_lvl'] < 5:
            update_user(user['id'], "points", user['points'] - cost)
            update_user(user['id'], "cooldown_lvl", user['cooldown_lvl'] + 1)
            await message.reply("⚡ Скорость увеличена!")
        else: await message.reply("❌ Недостаточно очков или макс. уровень!")
    elif choice == "2":
        cost = (user['luck_lvl'] + 1) * 300
        if user['points'] >= cost:
            update_user(user['id'], "points", user['points'] - cost)
            update_user(user['id'], "luck_lvl", user['luck_lvl'] + 1)
            await message.reply("🍀 Удача повышена!")
        else: await message.reply("❌ Недостаточно очков!")

@dp.message(F.text.lower() == "топ")
async def cmd_top(message: types.Message):
    conn = sqlite3.connect('cards_game.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, points FROM users ORDER BY points DESC LIMIT 10')
    top_users = cursor.fetchall()
    conn.close()
    
    text = "🏆 **ТОП ИГРОКОВ** 🏆\n"
    for i, (uid, pts) in enumerate(top_users, 1):
        text += f"{i}. ID {uid} — {pts} 💰\n"
    await message.answer(text)

async def main():
    init_db()
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
