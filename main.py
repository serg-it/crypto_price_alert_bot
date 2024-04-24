import asyncio
import logging
import os
import signal
import sqlite3
import sys
import json
from asyncio import Task
from typing import Tuple, Optional, Dict

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from symbols import get_all

TOKEN = os.getenv('TG_TOKEN')
assert TOKEN
dp = Dispatcher()
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))

conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS alerts (
    user_id INTEGER,
    price INTEGER
)
''')
conn.commit()

last_price: Optional[float] = None


class Alert(StatesGroup):
    symbol = State()
    price = State()


async def get_binance_rates() -> Dict[str, float]:
    async with aiohttp.ClientSession() as session:
        symbols = json.dumps(list(get_all())).replace(' ', '')
        params = {'symbols': symbols}
        async with session.get('https://api.binance.com/api/v3/ticker/price', params=params) as response:
            prices = {}
            for price in await response.json():
                # print(f'PRICE: {prices}')
                prices[price["symbol"]] = float(price["price"])
            # btc_to_usd = prices['USD']['last']
            # btc_to_rub = prices['RUB']['last']
            return prices


async def get_btc_rate() -> Tuple[float, float]:
    async with aiohttp.ClientSession() as session:
        async with session.get('https://blockchain.info/ticker') as response:
            prices = await response.json()
            btc_to_usd = prices['USD']['last']
            btc_to_rub = prices['RUB']['last']
            return float(btc_to_usd), float(btc_to_rub)


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
    c.execute("INSERT INTO alerts (user_id, price) VALUES (?, ?)", (user_id, alert_price))
    conn.commit()
    await message.reply(f"Установлено уведомление на цену {alert_price} USD")


@dp.message(Command('alerts'))
async def list_alerts(message: Message):
    user_id = message.chat.id
    c.execute("SELECT price FROM alerts WHERE user_id=?", (user_id,))
    alerts = c.fetchall()
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
    c.execute("DELETE FROM alerts WHERE user_id=?", (user_id,))
    conn.commit()
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
    c.execute("DELETE FROM alerts WHERE user_id=? AND price=?", (user_id, alert_price))
    conn.commit()
    if c.rowcount:
        await message.reply(f'Уведомление {alert_price} удалено.')
    else:
        await message.reply('Уведомление не найдено.')


async def check_alerts():
    global last_price
    while True:
        btc_to_usd, btc_to_rub = await get_btc_rate()
        if last_price:
            print(f'Got price {btc_to_usd}')
            c.execute("SELECT user_id, price FROM alerts")
            for user_id, alert_price in c.fetchall():
                if (last_price > alert_price >= btc_to_usd) or (last_price < alert_price <= btc_to_usd):
                    await bot.send_message(user_id, f'Цена биткоина достигла {btc_to_rub} RUB, {alert_price} USD')
                    c.execute("DELETE FROM alerts WHERE user_id=? AND price=?", (user_id, alert_price))
                    conn.commit()

        last_price = btc_to_usd
        await asyncio.sleep(60)


def tasks_handlers(*tasks) -> None:
    def stop_callback(sig: signal.Signals) -> None:
        task: Task
        for task in tasks:
            logging.warning("Received %s signal for task %s", sig.name, task.get_name())
            if not task.cancelled():
                task.cancel(f'Cancel task {task.get_name()}')

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGTERM, stop_callback, signal.SIGTERM)
    loop.add_signal_handler(signal.SIGINT, stop_callback, signal.SIGINT)


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
