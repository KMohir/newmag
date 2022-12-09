from aiogram.types import Message, CallbackQuery
from loader import dp, db
from .menu import delivery_status
from filters import IsUser


@dp.callback_query_handler(IsUser(), text=delivery_status)
async def process_delivery_status(query: CallbackQuery):
    orders = db.fetchall('SELECT * FROM orders WHERE cid=?', (query.message.chat.id,))

    if len(orders) == 0:
        await query.message.answer('У вас нет активных заказов.')
    else:
        await delivery_status_answer(query.message, orders)


async def delivery_status_answer(message, orders):
    res = ''

    for order in orders:
        res += f'Заказ <b>№{order[3]}</b>'
        answer = [
            ' лежит на складе.',
            ' уже в пути!',
            ' прибыл и ждет вас на почте!'
        ]

        res += answer[0]
        res += '\n\n'

    await message.answer(res)