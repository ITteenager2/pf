import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest
from config import TELEGRAM_TOKEN, ADMIN_USER_IDS
from database import init_db, add_user, get_user, update_user, get_all_users, import_products_from_csv, get_feedback_stats, add_support_request, add_recommendation
from ai_helper import generate_recommendation
from feedback import save_feedback
from google_sheets import update_google_sheets
from admin import handle_admin_command, get_bot_statistics, get_support_requests_list

logging.basicConfig(level=logging.INFO)

BOT_ID = None

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

FRAGRANCES = [
    ["Цветочные", "Древесные", "Цитрусовые", "Восточные", "Фужерные"],
    ["Шипровые", "Кожаные", "Гурманские", "Акватические", "Зеленые"],
    ["Пряные", "Фруктовые", "Альдегидные", "Мускусные", "Табачные"]
]
LOCATIONS = [
    ["Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург", "Казань"],
    ["Нижний Новгород", "Челябинск", "Самара", "Омск", "Ростов-на-Дону"],
    ["Уфа", "Красноярск", "Воронеж", "Пермь", "Волгоград"]
]


@dp.message(Command("start"))
async def start(message: types.Message):
    user = message.from_user
    user_data = get_user(user.id)
    if not user_data:
        add_user(user.id, user.first_name, user.last_name)
        logging.info(f"New user added: {user.id}")
    else:
        logging.info(f"Existing user: {user.id}")

    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="Получить рекомендацию", callback_data="get_recommendation"))
    keyboard.add(InlineKeyboardButton(text="Обновить предпочтения", callback_data="update_preferences"))
    
    if str(user.id) in ADMIN_USER_IDS:
        keyboard.add(InlineKeyboardButton(text="Админ-панель", callback_data="admin_panel"))
    
    keyboard.adjust(1)

    await message.reply(
        f'Привет, {user.first_name}! Я ваш персональный консультант по парфюмерии. Что бы вы хотели сделать?\nРекомендую для начала обновить предпочтения!',
        reply_markup=keyboard.as_markup()
    )

@dp.callback_query(lambda c: c.data == "get_recommendation")
async def get_recommendation_callback(callback_query: CallbackQuery):
    user_data = get_user(callback_query.from_user.id)
    if not user_data or not user_data.get('gender') or not user_data.get('preferred_fragrances'):
        await callback_query.message.answer("Для получения рекомендации нужно указать пол и предпочитаемые ароматы. Пожалуйста, обновите ваши предпочтения.")
        await update_preferences_callback(callback_query)
    else:
        await callback_query.message.answer("Генерирую рекомендацию, это может занять несколько секунд...")
        recommendation = await generate_recommendation(user_data)
        await callback_query.message.answer(recommendation)
        await ask_feedback(callback_query.message)
    await callback_query.answer()

@dp.callback_query(lambda c: c.data == "update_preferences")
async def update_preferences_callback(callback_query: CallbackQuery):
    await ask_age(callback_query.message)
    await callback_query.answer()

async def ask_age(message: types.Message):
    await message.answer("Пожалуйста, введите ваш возраст:")

@dp.message(lambda message: message.text and message.text.isdigit())
async def process_age_input(message: types.Message):
    user_age = message.text
    update_user(message.from_user.id, 'age', user_age)
    await message.answer(f"Ваш возраст ({user_age}) сохранен. Пожалуйста, продолжите выбор предпочтений.")
    await ask_gender(message)

@dp.message(lambda message: message.text and not message.text.isdigit())
async def handle_non_digit_input(message: types.Message):
    await message.answer("Пожалуйста, введите числовое значение для возраста.")

async def ask_gender(message: types.Message):
    keyboard = InlineKeyboardBuilder()
    genders = ["Мужской", "Женский", "Другой"]
    for gender in genders:
        keyboard.add(InlineKeyboardButton(text=gender, callback_data=f"gender_{gender.lower()}"))
    keyboard.adjust(1)
    await message.answer("Выберите ваш пол:", reply_markup=keyboard.as_markup())

@dp.callback_query(lambda c: c.data.startswith("gender_"))
async def process_gender(callback_query: CallbackQuery):
    gender = callback_query.data.split("_")[1]
    update_user(callback_query.from_user.id, "gender", gender)

    try:
        await callback_query.message.edit_reply_markup(reply_markup=None)
        await callback_query.message.answer(f"Вы выбрали: {gender.capitalize()}.\nСпасибо за ваш выбор!")
        await ask_fragrances(callback_query.message)
    except TelegramBadRequest as e:
        logging.error(f"Ошибка при редактировании сообщения: {e}")
    except Exception as e:
        logging.error(f"Неизвестная ошибка: {e}")
    finally:
        await callback_query.answer()

async def ask_fragrances(message: types.Message, page=0):
    keyboard = InlineKeyboardBuilder()
    for fragrance in FRAGRANCES[page]:
        keyboard.add(InlineKeyboardButton(text=fragrance, callback_data=f"fragrance_{fragrance}"))
    if page < len(FRAGRANCES) - 1:
        keyboard.add(InlineKeyboardButton(text="Следующая страница", callback_data=f"fragrance_next_{page+1}"))
    keyboard.add(InlineKeyboardButton(text="Завершить выбор", callback_data="finish_fragrances"))
    keyboard.adjust(1)
    await message.answer('Выберите предпочитаемые ароматы (можно выбрать несколько):', reply_markup=keyboard.as_markup())

@dp.callback_query(lambda c: c.data.startswith('fragrance_'))
async def process_fragrance(callback_query: CallbackQuery):
    data = callback_query.data.split('_')
    if data[1] == 'next':
        page = int(data[2])
        await ask_fragrances(callback_query.message, page)
    else:
        fragrance = '_'.join(data[1:])
        user_data = get_user(callback_query.from_user.id)
        fragrances = user_data.get('preferred_fragrances', []) if user_data else []
        if fragrance not in fragrances:
            fragrances.append(fragrance)
        update_user(callback_query.from_user.id, 'preferred_fragrances', fragrances)
        await callback_query.answer(text=f"Вы выбрали: {fragrance}. Можете выбрать ещё или завершить выбор.")

@dp.callback_query(lambda c: c.data == "finish_fragrances")
async def finish_fragrances(callback_query: CallbackQuery):
    await callback_query.message.edit_reply_markup(reply_markup=None)
    await callback_query.message.answer("Спасибо за ваши предпочтения!")
    await ask_location(callback_query.message)
    await callback_query.answer()

async def ask_location(message: types.Message):
    keyboard = InlineKeyboardBuilder()
    for location in LOCATIONS[0]:
        keyboard.add(InlineKeyboardButton(text=location, callback_data=f"location_{location}"))
    keyboard.add(InlineKeyboardButton(text="Другой город", callback_data="location_other"))
    keyboard.adjust(1)
    await message.answer('Выберите ваше местоположение:', reply_markup=keyboard.as_markup())

@dp.callback_query(lambda c: c.data.startswith('location_'))
async def process_location(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    logging.info(f"Processing location for user_id={user_id}")

    data = callback_query.data.split('_')
    if data[1] == 'other':
        await callback_query.message.answer("Пожалуйста, введите название вашего города:")
    else:
        location = '_'.join(data[1:])
        update_user(user_id, 'location', location)
        await callback_query.message.edit_reply_markup(reply_markup=None)
        await finish_survey(callback_query)
    await callback_query.answer()


@dp.message(lambda message: message.text and not message.text.startswith('/'))
async def process_custom_location(message: types.Message):
    user_id = message.from_user.id
    update_user(user_id, 'location', message.text)
    user_data = get_user(user_id)
    if not user_data:
        await message.answer("Произошла ошибка при получении данных пользователя. Пожалуйста, попробуйте обновить предпочтения.")
        return
    await message.answer("Генерирую рекомендацию, это может занять несколько секунд...")
    recommendation = await generate_recommendation(user_data)
    await message.answer(f'Спасибо за ответы! Вот моя рекомендация для вас:\n\n{recommendation}')
    await ask_feedback(message)

async def finish_survey(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user_data = get_user(user_id)
    if not user_data:
        await callback_query.message.answer("Произошла ошибка при получении данных пользователя. Пожалуйста, попробуйте обновить предпочтения.")
        return
    await callback_query.message.answer("Генерирую рекомендацию, это может занять несколько секунд...")
    recommendation = await generate_recommendation(user_data)
    await callback_query.message.answer(f'Спасибо за ответы! Вот моя рекомендация для вас:\n\n{recommendation}')
    await ask_feedback(callback_query.message)

async def ask_feedback(message: types.Message):
    keyboard = InlineKeyboardBuilder()
    for i in range(1, 6):
        keyboard.add(InlineKeyboardButton(text=f"{i} звезд", callback_data=f"feedback_{i}"))
    keyboard.adjust(1)
    await message.answer("Оцените мои рекомендации (от 1 до 5):", reply_markup=keyboard.as_markup())

@dp.callback_query(lambda c: c.data.startswith('feedback_'))
async def process_feedback(callback_query: CallbackQuery):
    feedback = int(callback_query.data.split('_')[1])
    save_feedback(callback_query.from_user.id, feedback)
    await callback_query.answer(text="Спасибо за ваш отзыв!")
    await callback_query.message.answer("Мы продолжим работу над улучшением рекомендаций для вас!")

@dp.message()
async def handle_message(message: types.Message):
    if message.from_user.id == bot.id:
        return  # Игнорируем сообщения от самого бота

    user_data = get_user(message.from_user.id)
    if not user_data or not user_data.get('gender') or not user_data.get('preferred_fragrances'):
        await message.reply("Для получения рекомендации нужно указать пол и предпочитаемые ароматы. Пожалуйста, обновите ваши предпочтения.")
        await update_preferences_callback(types.CallbackQuery(message=message, from_user=message.from_user, chat_instance="", data="update_preferences"))
    else:
        await message.reply("Генерирую рекомендацию, это может занять несколько секунд...")
        response = await generate_recommendation(user_data, message.text)
        await message.reply(response)
        add_recommendation(message.from_user.id, response)
        await ask_feedback(message)

@dp.message(Command("admin"))
async def admin_command(message: types.Message):
    if str(message.from_user.id) in ADMIN_USER_IDS:
        await handle_admin_command(message)
    else:
        await message.reply("У вас нет доступа к админ-панели.")

@dp.callback_query(lambda c: c.data == "admin_stats")
async def admin_stats(callback_query: CallbackQuery):
    if str(callback_query.from_user.id) in ADMIN_USER_IDS:
        stats = await get_bot_statistics()
        await callback_query.message.answer(stats)
    await callback_query.answer()

@dp.callback_query(lambda c: c.data == "admin_support")
async def admin_support(callback_query: CallbackQuery):
    if str(callback_query.from_user.id) in ADMIN_USER_IDS:
        support_requests = await get_support_requests_list()
        await callback_query.message.answer(support_requests)
    await callback_query.answer()

async def send_recommendations():
    users = get_all_users()
    for user in users:
        recommendation = await generate_recommendation(user)
        try:
            await bot.send_message(chat_id=user['id'], text=f"Новая рекомендация для вас:\n\n{recommendation}")
        except Exception as e:
            logging.error(f"Failed to send recommendation to user {user['id']}: {str(e)}")

async def update_analytics():
    feedback_stats = get_feedback_stats()
    update_google_sheets(feedback_stats)

async def scheduler():
    while True:
        await asyncio.sleep(86400)  # 24 hours
        await send_recommendations()
        await update_analytics()

async def main():
    try:
        global BOT_ID
        # Инициализация ID бота
        bot_info = await bot.get_me()
        BOT_ID = bot_info.id
        logging.info(f"Bot initialized with username: {bot_info.username}, id: {BOT_ID}")
        
        init_db()
        import_products_from_csv('edpby.csv')
        asyncio.create_task(scheduler())
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Error in main function: {e}")
        raise


if __name__ == '__main__':
    asyncio.run(main())

