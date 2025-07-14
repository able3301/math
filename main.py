import json
import os
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN", "8097862138:AAGTLV5n42GHd8ak5naciQq8oCm-epxFvNk")  # <-- SHU YERGA BOT TOKEN KIRITING
ADMIN_ID = int(os.getenv("ADMIN_ID", "1350513135"))         # <-- SHU YERGA ADMIN ID kiriting

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

USERS_FILE = "users.json"
LESSONS_FILE = "lessons.json"
PURCHASES_FILE = "purchases.json"

# Fayllarni tekshirish
for file in [USERS_FILE, LESSONS_FILE, PURCHASES_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump([], f)

# JSON funksiyalar
def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# Holatlar
class Register(StatesGroup):
    name = State()
    age = State()

class AddLesson(StatesGroup):
    name = State()
    price = State()
    video = State()

# START
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    users = load_json(USERS_FILE)
    user_id = message.from_user.id
    if not any(u["user_id"] == user_id for u in users):
        markup = ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("📝 Roʻyxatdan oʻtish"))
        await message.answer("Assalomu alaykum! Avval roʻyxatdan oʻting:", reply_markup=markup)
    else:
        await show_main_menu(message)

# RO‘YXATDAN O‘TISH
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
        await message.answer("Iltimos, raqam kiriting:")
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
    await message.answer("✅ Ro'yxatdan o'tish yakunlandi!")
    await show_main_menu(message)

# MAIN MENU
async def show_main_menu(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📚 Darslar", "📘 Mening darslarim")
    markup.add("🧾 Toʻlov chekini yuborish", "❓ Yordam")
    await message.answer("Kerakli bo‘limni tanlang:", reply_markup=markup)

# DARSLAR
@dp.message_handler(lambda msg: msg.text == "📚 Darslar")
async def show_lessons(message: types.Message):
    lessons = load_json(LESSONS_FILE)
    if not lessons:
        await message.answer("Hozircha hech qanday dars mavjud emas.")
        return

    markup = InlineKeyboardMarkup(row_width=1)
    for lesson in lessons:
        markup.add(InlineKeyboardButton(lesson["name"], callback_data=f"lesson_{lesson['id']}"))

    await message.answer("Quyidagi darslardan birini tanlang:", reply_markup=markup)

@dp.callback_query_handler(lambda c: c.data.startswith("lesson_"))
async def lesson_selected(callback: types.CallbackQuery):
    lesson_id = callback.data.split("_")[1]
    lessons = load_json(LESSONS_FILE)
    lesson = next((l for l in lessons if l["id"] == lesson_id), None)

    if not lesson:
        await callback.message.answer("Dars topilmadi.")
        return

    # Foydalanuvchi tanlagan darsni `pending` ro'yxatga yozamiz
    purchases = load_json(PURCHASES_FILE)
    purchases.append({
        "user_id": callback.from_user.id,
        "lesson_id": lesson_id,
        "status": "pending",
        "date": datetime.now().strftime("%Y-%m-%d")
    })
    save_json(PURCHASES_FILE, purchases)

    text = (
        f"📘 *{lesson['name']}*\n"
        f"💰 Narxi: {lesson['price']} so'm\n"
        f"📹 Video link: {lesson['video']}\n\n"
        f"⬆️ Endi to‘lovni amalga oshirib, chekni yuboring."
    )
    await callback.message.answer(text, parse_mode="Markdown")
    await show_main_menu(callback.message)

# TO‘LOV
@dp.message_handler(content_types=types.ContentType.PHOTO)
async def receive_payment(message: types.Message):
    purchases = load_json(PURCHASES_FILE)
    pending = [p for p in purchases if p["user_id"] == message.from_user.id and p["status"] == "pending"]
    if not pending:
        await message.answer("Siz hali hech qanday dars tanlamagansiz.")
        return

    photo = message.photo[-1]
    file_id = photo.file_id
    caption = (
        f"🧾 Yangi to‘lov\n"
        f"👤 User: {message.from_user.full_name}\n"
        f"🆔 ID: {message.from_user.id}"
    )
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{message.from_user.id}"),
        InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_{message.from_user.id}")
    )
    await bot.send_photo(chat_id=ADMIN_ID, photo=file_id, caption=caption, reply_markup=markup)
    await message.answer("✅ Toʻlov cheki yuborildi. Admin tasdiqlashini kuting.")

# ADMIN TO‘LOVNI TASDIQLASHI
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
        await bot.send_message(user_id, f"Toʻlovingiz admin tomonidan {'✅ tasdiqlandi' if action == 'approve' else '❌ rad etildi'}")
        await callback.answer("Holat yangilandi.")
    else:
        await callback.answer("Toʻlov topilmadi.")

# Mening darslarim
@dp.message_handler(lambda msg: msg.text == "📘 Mening darslarim")
async def show_my_lessons(message: types.Message):
    purchases = load_json(PURCHASES_FILE)
    lessons = load_json(LESSONS_FILE)
    my = [p for p in purchases if p["user_id"] == message.from_user.id and p["status"] == "tasdiqlangan"]
    if not my:
        await message.answer("Siz hali hech qanday dars sotib olmadingiz.")
        return
    markup = InlineKeyboardMarkup()
    for p in my:
        lesson = next((l for l in lessons if l["id"] == p["lesson_id"]), None)
        if lesson:
            markup.add(InlineKeyboardButton(lesson["name"], url=lesson["video"]))
    await message.answer("📚 Mening darslarim:", reply_markup=markup)

# Yordam
@dp.message_handler(lambda msg: msg.text == "❓ Yordam")
async def help_msg(message: types.Message):
    await message.answer("Yordam uchun admin bilan bog‘laning.")

# ADMIN DARSLAR QO‘SHISH
@dp.message_handler(commands=["add_lesson"])
async def add_lesson(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await AddLesson.name.set()
    await message.answer("Yangi dars nomini kiriting:")

@dp.message_handler(state=AddLesson.name)
async def get_lesson_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await AddLesson.next()
    await message.answer("Narxini kiriting (so‘m):")

@dp.message_handler(state=AddLesson.price)
async def get_lesson_price(message: types.Message, state: FSMContext):
    try:
        price = int(message.text.strip())
    except:
        await message.answer("Raqam kiriting.")
        return
    await state.update_data(price=price)
    await AddLesson.next()
    await message.answer("Video havolasini kiriting:")

@dp.message_handler(state=AddLesson.video)
async def save_lesson(message: types.Message, state: FSMContext):
    data = await state.get_data()
    video = message.text.strip()
    lessons = load_json(LESSONS_FILE)
    lessons.append({"id": str(len(lessons)+1), "name": data["name"], "price": data["price"], "video": video})
    save_json(LESSONS_FILE, lessons)
    await state.finish()
    await message.answer("✅ Dars qo‘shildi.")

# START POLLING
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True)
