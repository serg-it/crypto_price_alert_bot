from typing import Iterable

symbols = {
    'crypto': [
        'BTC',
        'ETH',
        'BNB',
        'SOL',
        'XRP',
    ],
    'fiat': [
        'USDT',
        'EUR',
        'RUB',
        'TRY',
    ]
}


def get_all() -> Iterable[str]:
    for crypto in symbols['crypto']:
        for fiat in symbols['fiat']:
            yield crypto + fiat
