import asyncio
import logging
import os
import sqlite3
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, BotCommand
from requests import get

TOKEN = os.getenv('TG_TOKEN')
assert TOKEN
dp = Dispatcher()
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2))

conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS alerts (
    user_id INTEGER,
    price INTEGER
)
''')
conn.commit()


def get_btc_rate():
    response = get('https://blockchain.info/ticker').json()
    btc_to_usd = response['USD']['last']
    btc_to_rub = response['RUB']['last']
    return btc_to_usd, btc_to_rub


@dp.message(CommandStart())
async def send_welcome(message: Message):
    btc_to_usd, btc_to_rub = get_btc_rate()
    await message.reply(f"Текущий курс BTC: {btc_to_usd} USD, {btc_to_rub} RUB")


@dp.message(command='help')
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


@dp.message(commands=['alert'])
async def set_alert(message: Message):
    try:
        alert_price = int(message.text.split()[1])
    except (ValueError, TypeError):
        await message.reply("Значение курса должно быть целое число")
        return
    except IndexError:
        await message.reply(f'Команда должна быть в следующем формате: */alert price*, где price - целое число')
        return

    user_id = message.chat.id
    c.execute("INSERT INTO alerts (user_id, price) VALUES (?, ?)", (user_id, alert_price))
    conn.commit()
    await message.reply(f"Установлено уведомление на цену {alert_price} USD")


@dp.message(commands=['alerts'])
async def list_alerts(message: Message):
    user_id = message.chat.id
    c.execute("SELECT price FROM alerts WHERE user_id=?", (user_id,))
    alerts = c.fetchall()
    if alerts:
        reply = "Активные уведомления:\n"
        for alert in alerts:
            reply += f"Цена: {alert[0]} USD\n"
    else:
        reply = "Нет активных уведомлений."
    await message.reply(reply)


@dp.message(commands=['clear'])
async def clear_alerts(message: Message):
    user_id = message.chat.id
    c.execute("DELETE FROM alerts WHERE user_id=?", (user_id,))
    conn.commit()
    await message.reply("Все уведомления удалены.")


@dp.message(commands=['del'])
async def delete_alert(message: Message):
    try:
        alert_price = int(message.text.split()[1])
    except (ValueError, TypeError):
        await message.reply("Значение цены должно быть целое число")
        return
    except IndexError:
        await message.reply(f'Команда должна быть в следующем формате: "/del price", где price - целое число')
        return

    user_id = message.chat.id
    c.execute("DELETE FROM alerts WHERE user_id=? AND price=?", (user_id, alert_price))
    conn.commit()
    if c.rowcount:
        await message.reply(f"Уведомление {alert_price} удалено.")
    else:
        await message.reply("Уведомление не найдено.")


async def check_alerts():
    while True:
        btc_to_usd, btc_to_rub = get_btc_rate()
        c.execute("SELECT user_id, price FROM alerts")
        for user_id, alert_price in c.fetchall():
            if btc_to_usd >= alert_price:
                await bot.send_message(user_id, f"Уведомление: цена биткоина достигла {btc_to_rub} RUB, {alert_price} USD")
                c.execute("DELETE FROM alerts WHERE user_id=? AND price=?", (user_id, alert_price))
                conn.commit()
        await asyncio.sleep(60)  # Проверка каждые 60 секунд


async def run_bot() -> None:
    # And the run events dispatching
    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    loop = asyncio.get_event_loop()
    loop.create_task(run_bot())
    loop.create_task(check_alerts())
