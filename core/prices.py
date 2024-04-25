import json
from typing import Dict, Tuple

import aiohttp

from core.symbols import get_all


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
