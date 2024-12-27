from aiogram import Bot, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import get_all_users, get_support_requests, get_recommendation_count, get_support_request_count

async def handle_admin_command(message: types.Message):
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Статистика", callback_data="admin_stats")
    keyboard.button(text="Обращения в поддержку", callback_data="admin_support")
    keyboard.adjust(2)
    await message.answer("Выберите действие:", reply_markup=keyboard.as_markup())

async def send_broadcast(bot: Bot, message: str, admin_chat_id: int):
    await bot.send_message(chat_id=admin_chat_id, text="Введите текст для рассылки:")

    # Note: The following part should be integrated into your main message handler
    # This is just a placeholder for the logic
    async def handle_broadcast_text(msg: types.Message):
        broadcast_message = msg.text
        users = get_all_users()
        success_count = 0
        for user in users:
            try:
                await bot.send_message(chat_id=int(user['id']), text=broadcast_message)
                success_count += 1
            except Exception as e:
                print(f"Failed to send broadcast to user {user['id']}: {str(e)}")

        await bot.send_message(chat_id=admin_chat_id, text=f"Рассылка завершена. Успешно отправлено: {success_count} из {len(users)} пользователей.")

async def get_bot_statistics():
    total_users = len(get_all_users())
    total_support_requests = get_support_request_count()
    total_recommendations = get_recommendation_count()
    
    stats = f"Статистика бота:\n\n"
    stats += f"Всего пользователей: {total_users}\n"
    stats += f"Всего обращений в поддержку: {total_support_requests}\n"
    stats += f"Всего выданных рекомендаций: {total_recommendations}"
    
    return stats

async def get_support_requests_list():
    requests = get_support_requests()
    message = "Последние обращения в поддержку:\n\n"
    for req in requests:
        message += f"От: {req['user_id']}\n"
        message += f"Сообщение: {req['message']}\n"
        if req['photo_id']:
            message += "Прикреплено фото\n"
        message += f"Дата: {req['timestamp']}\n\n"
    return message

