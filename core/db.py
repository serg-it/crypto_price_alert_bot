from typing import Optional

from databases import Database

database = Database('sqlite+aiosqlite:///db.sqlite3')


async def db_prepare() -> None:
    query_alerts = 'CREATE TABLE IF NOT EXISTS alerts (user_id INTEGER, price INTEGER)'
    await database.connect()
    await database.execute(query=query_alerts)


async def new_alert(user_id: int, price: int) -> None:
    if not await get_user_alerts(user_id, price):
        query = "INSERT INTO alerts (user_id, price) VALUES (:user_id, :price)"
        return await database.execute(query=query, values={'user_id': user_id, 'price': price})


async def get_user_alerts(user_id: int, price: Optional[int] = None):
    query = "SELECT price FROM alerts WHERE user_id = :user_id"
    values = {'user_id': user_id}
    if price is not None:
        query += " AND price = :price"
        values['price'] = price
    return await database.fetch_all(query=query, values=values)


async def get_alerts_by_price(from_price: float, to_price: float):
    query = "SELECT * FROM alerts WHERE price >= :min_price AND price <= :max_price"
    values = {
        'min_price': to_price,
        'max_price': from_price,
    }
    if from_price < to_price:
        values = {
            'min_price': from_price,
            'max_price': to_price,
        }
    return await database.fetch_all(query=query, values=values)


async def delete_alerts(user_id: int, price: Optional[int]):
    query = "DELETE FROM alerts WHERE user_id = :user_id"
    values = {'user_id': user_id}
    if price is not None:
        query += " AND price = :price"
        values['price'] = price
    return await database.execute(query=query, values=values)
