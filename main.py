import asyncio
import logging
import sys

from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from core.alerts import check_alerts
from core.db import get_user_alerts, delete_alerts, new_alert
from core.handlers import tasks_handlers
from core.prices import get_binance_rates
from core.tg import dp, bot


class Alert(StatesGroup):
    symbol = State()
    price = State()


@dp.message(CommandStart())
async def send_welcome(message: Message):
    prices = await get_binance_rates()
    prices_str = ''
    # for symb, price in prices.items():
    #     prices_str += f'\n*{symb}*: {price}'
    await bot.send_message(message.chat.id,
                           f"Текущий курс Bitcoin: {prices['BTCUSDT']} USD\n"
                           f"А еще ты можешь посмотреть другие курсы и создать уведомления о достижении цены",
                           reply_markup=InlineKeyboardMarkup(
                               inline_keyboard=[
                                   [
                                       InlineKeyboardButton(text="Посмотреть курсы валют", callback_data="start"),
                                       InlineKeyboardButton(text="Создать уведомление", callback_data="alert")
                                   ]
                               ]
                           ),
                           # reply_markup=ReplyKeyboardMarkup(
                           #     keyboard=[
                           #         [
                           #             KeyboardButton(text="Посмотреть курсы валют",),
                           #             KeyboardButton(text="Создать уведомление"),
                           #         ]
                           #     ],
                           #     resize_keyboard=True,
                           # ),
                           )


@dp.message(Command('help'))
async def send_help(message: Message):
    help_text = """
Команды бота:
/start - получение текущего курса биткоина в рублях и долларах
/alert {price} - установка уведомления при достижении курса биткоина указанной суммы в долларах
/alerts - просмотр всех активных уведомлений
/clear - удаление всех активных уведомлений
/del {price} - удаление уведомления цены
/help - список всех команд бота
"""
    await message.reply(help_text)


@dp.message(Command('alert'))
async def set_alert(message: Message):
    try:
        assert message.text
        alert_price = int(message.text.split()[1])
    except (ValueError, TypeError):
        await message.reply('Значение курса должно быть целое число')
        return
    except IndexError:
        await message.reply('Команда должна быть в формате: /alert price, где price - целое число')
        return

    user_id = message.chat.id
    await new_alert(user_id, alert_price)
    await message.reply(f"Установлено уведомление на цену {alert_price} USD")


@dp.message(Command('alerts'))
async def list_alerts(message: Message):
    user_id = message.chat.id
    alerts = await get_user_alerts(user_id)
    if alerts:
        reply = 'Активные уведомления:\n'
        for alert in alerts:
            reply += f'Цена: {alert[0]} USD\n'
    else:
        reply = 'Нет активных уведомлений.'
    await message.reply(reply)


@dp.message(Command('clear'))
async def clear_alerts(message: Message):
    """Clear all alerts"""
    user_id = message.chat.id
    await delete_alerts(user_id, None)
    await message.reply('Все уведомления удалены')


@dp.message(Command('del'))
async def delete_alert(message: Message):
    """Delete the alert"""
    try:
        assert message.text
        alert_price = int(message.text.split()[1])
    except (ValueError, TypeError):
        await message.reply('Значение цены должно быть целое число')
        return
    except IndexError:
        await message.reply('Команда должна быть в формате: "/del price", где price - целое число')
        return

    user_id = message.chat.id
    await delete_alerts(user_id, alert_price)
    await message.reply(f'Уведомление {alert_price} удалено.')
    # else:
    #     await message.reply('Уведомление не найдено.')


async def main() -> None:
    bot_task = asyncio.create_task(dp.start_polling(bot, handle_signals=False), name='Bot-task')
    alert_task = asyncio.create_task(check_alerts(), name='Alert-task')
    tasks_handlers(alert_task, bot_task)
    try:
        await asyncio.gather(bot_task, alert_task)
    except asyncio.CancelledError as e:
        logging.info(e)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
