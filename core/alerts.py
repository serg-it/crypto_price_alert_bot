import asyncio
from typing import Optional

from core.db import delete_alerts, get_alerts_by_price
from core.prices import get_btc_rate
from core.tg import bot

last_price: Optional[float] = None


async def check_alerts():
    global last_price
    while True:
        btc_to_usd, btc_to_rub = await get_btc_rate()
        print(f'Got price {btc_to_usd}')
        if last_price:
            for alert in await get_alerts_by_price(last_price, btc_to_usd):
                print(f'USER: {alert}')
                print(f'PRICE: {alert.price}')
                await bot.send_message(alert.user_id, f'Цена биткоина достигла {alert.price} USD')
                await delete_alerts(alert.user_id, alert.price)
                await asyncio.sleep(1)

        last_price = btc_to_usd
        await asyncio.sleep(50)
