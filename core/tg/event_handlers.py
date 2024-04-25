from core.db import db_prepare, database
from core.tg import dp


@dp.startup()
async def bot_start():
    await db_prepare()


@dp.shutdown()
async def bot_shutdown():
    await database.disconnect()
