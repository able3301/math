
import json
import os
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN", "8097862138:AAGTLV5n42GHd8ak5naciQq8oCm-epxFvNk")
ADMIN_ID = int(os.getenv("ADMIN_ID", "1350513135"))

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

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

class Register(StatesGroup):
    name = State()
    age = State()

class AddLesson(StatesGroup):
    name = State()
    price = State()
    video = State()

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
    await Register.name.set()
    await message.answer("Ismingizni kiriting:")

@dp.message_handler(state=Register.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await Register.next()
    await message.answer("Yoshingizni kiriting:")

@dp.message_handler(state=Register.age)
async def save_user(message: types.Message, state: FSMContext):
    try:
        age = int(message.text.strip())
    except ValueError:
        await message.answer("Iltimos, raqam ko'rinishida yosh kiriting:")
        return
    data = await state.get_data()
    user = {
        "user_id": message.from_user.id,
        "name": data["name"],
        "age": age,
        "username": message.from_user.username,
        "date": datetime.now().strftime("%Y-%m-%d")
    }
    users = load_json(USERS_FILE)
    users.append(user)
    save_json(USERS_FILE, users)
    await state.finish()
    await message.answer("Ro'yxatdan o'tish muvaffaqiyatli yakunlandi.")
    await show_main_menu(message)

async def show_main_menu(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📚 Darslar", "📘 Mening darslarim")
    markup.add("🧾 Toʻlov chekini yuborish", "❓ Yordam")
    await message.answer("Kerakli boʻlimni tanlang:", reply_markup=markup)

@dp.message_handler(commands=["add_lesson"])
async def add_lesson(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await AddLesson.name.set()
    await message.answer("Yangi dars nomini yuboring:")

@dp.message_handler(state=AddLesson.name)
async def get_lesson_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await AddLesson.next()
    await message.answer("Dars narxini so'mda kiriting:")

@dp.message_handler(state=AddLesson.price)
async def get_lesson_price(message: types.Message, state: FSMContext):
    try:
        price = int(message.text.strip())
    except ValueError:
        await message.answer("Iltimos, raqam kiriting:")
        return
    await state.update_data(price=price)
    await AddLesson.next()
    await message.answer("Dars videosi havolasini kiriting:")

@dp.message_handler(state=AddLesson.video)
async def save_lesson(message: types.Message, state: FSMContext):
    data = await state.get_data()
    video = message.text.strip()
    lessons = load_json(LESSONS_FILE)
    lessons.append({"id": str(len(lessons) + 1), "name": data["name"], "price": data["price"], "video": video})
    save_json(LESSONS_FILE, lessons)
    await state.finish()
    await message.answer("✅ Dars muvaffaqiyatli qo'shildi.")

# The rest of your existing handlers (darslar, to'lov, tasdiq, reject, etc.) shu holatda qoladi

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True)
