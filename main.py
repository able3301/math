
import json
import os
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))

bot = Bot(token="8097862138:AAGTLV5n42GHd8ak5naciQq8oCm-epxFvNk")
dp = Dispatcher(bot)

USERS_FILE = "users.json"
LESSONS_FILE = "lessons.json"
PURCHASES_FILE = "purchases.json"

for file in [USERS_FILE, LESSONS_FILE, PURCHASES_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump([], f)

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    users = load_json(USERS_FILE)
    user_id = message.from_user.id
    if not any(u["user_id"] == user_id for u in users):
        markup = ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("📝 Roʻyxatdan oʻtish"))
        await message.answer("Assalomu alaykum! Avval roʻyxatdan oʻting:", reply_markup=markup)
    else:
        await show_main_menu(message)

@dp.message_handler(lambda msg: msg.text == "📝 Roʻyxatdan oʻtish")
async def register(message: types.Message):
    users = load_json(USERS_FILE)
    if any(u["user_id"] == message.from_user.id for u in users):
        await message.answer("Siz allaqachon ro'yxatdan o'tgansiz.")
        return
    await message.answer("Ismingizni kiriting:")
    dp.register_message_handler(get_name, state="awaiting_name")

async def get_name(message: types.Message):
    name = message.text.strip()
    dp.current_state().finish()
    await message.answer("Yoshingizni kiriting:")
    dp.register_message_handler(lambda msg: save_user(msg, name), state="awaiting_age")

async def save_user(message: types.Message, name):
    try:
        age = int(message.text.strip())
    except ValueError:
        await message.answer("Iltimos, raqam ko'rinishida yosh kiriting:")
        return
    user = {
        "user_id": message.from_user.id,
        "name": name,
        "age": age,
        "username": message.from_user.username,
        "date": datetime.now().strftime("%Y-%m-%d")
    }
    users = load_json(USERS_FILE)
    users.append(user)
    save_json(USERS_FILE, users)
    dp.current_state().finish()
    await message.answer("Ro'yxatdan o'tish muvaffaqiyatli yakunlandi.")
    await show_main_menu(message)

async def show_main_menu(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📚 Darslar", "📘 Mening darslarim")
    markup.add("🧾 Toʻlov chekini yuborish", "❓ Yordam")
    await message.answer("Kerakli boʻlimni tanlang:", reply_markup=markup)

@dp.message_handler(lambda msg: msg.text == "📚 Darslar")
async def show_lessons(message: types.Message):
    lessons = load_json(LESSONS_FILE)
    if not lessons:
        await message.answer("Hozircha hech qanday dars mavjud emas.")
        return
    markup = InlineKeyboardMarkup()
    for l in lessons:
        markup.add(InlineKeyboardButton(f"{l['name']} - {l['price']} so'm", callback_data=f"lesson_{l['id']}"))
    await message.answer("Quyidagi darslardan birini tanlang:", reply_markup=markup)

@dp.callback_query_handler(lambda c: c.data.startswith("lesson_"))
async def lesson_selected(callback: types.CallbackQuery):
    lesson_id = callback.data.split("_")[1]
    purchases = load_json(PURCHASES_FILE)
    purchases.append({
        "user_id": callback.from_user.id,
        "lesson_id": lesson_id,
        "status": "pending",
        "date": datetime.now().strftime("%Y-%m-%d")
    })
    save_json(PURCHASES_FILE, purchases)
    await callback.message.answer("Dars tanlandi. Endi to'lovni amalga oshiring va chekni yuboring.")
    await show_main_menu(callback.message)

@dp.message_handler(content_types=types.ContentType.PHOTO)
async def receive_payment(message: types.Message):
    purchases = load_json(PURCHASES_FILE)
    pending = [p for p in purchases if p["user_id"] == message.from_user.id and p["status"] == "pending"]
    if not pending:
        await message.answer("Avval dars tanlang.")
        return
    photo = message.photo[-1]
    file_id = photo.file_id
    caption = (
    f" Yangi to'lov\n"
    f"User: {message.from_user.full_name}\n"
    f"ID: {message.from_user.id}"
)
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{message.from_user.id}"),
        InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_{message.from_user.id}")
    )
    await bot.send_photo(chat_id=ADMIN_ID, photo=file_id, caption=caption, reply_markup=markup)
    await message.answer("Toʻlov cheki yuborildi. Admin tasdiqlashini kuting.")

@dp.callback_query_handler(lambda c: c.data.startswith("approve_") or c.data.startswith("reject_"))
async def handle_admin_decision(callback: types.CallbackQuery):
    action, user_id = callback.data.split("_")
    user_id = int(user_id)
    purchases = load_json(PURCHASES_FILE)
    updated = False
    for p in purchases:
        if p["user_id"] == user_id and p["status"] == "pending":
            p["status"] = "tasdiqlangan" if action == "approve" else "rad etilgan"
            updated = True
    if updated:
        save_json(PURCHASES_FILE, purchases)
        await bot.send_message(user_id, "Toʻlovingiz admin tomonidan " + ("✅ tasdiqlandi" if action == "approve" else "❌ rad etildi"))
        await callback.answer("Foydalanuvchiga xabar yuborildi.")
    else:
        await callback.answer("Hech qanday to'lov topilmadi.")

@dp.message_handler(lambda msg: msg.text == "📘 Mening darslarim")
async def show_my_lessons(message: types.Message):
    purchases = load_json(PURCHASES_FILE)
    lessons = load_json(LESSONS_FILE)
    user_purchases = [p for p in purchases if p["user_id"] == message.from_user.id and p["status"] == "tasdiqlangan"]
    if not user_purchases:
        await message.answer("Siz hali hech qanday dars sotib olmadingiz.")
        return
    markup = InlineKeyboardMarkup()
    for p in user_purchases:
        lesson = next((l for l in lessons if l["id"] == p["lesson_id"]), None)
        if lesson:
            markup.add(InlineKeyboardButton(f"{lesson['name']}", url=lesson["video"]))
    await message.answer("Sotib olingan darslaringiz:", reply_markup=markup)

@dp.message_handler(lambda msg: msg.text == "❓ Yordam")
async def help_message(message: types.Message):
    await message.answer("Yordam uchun admin bilan bog‘laning.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True)
