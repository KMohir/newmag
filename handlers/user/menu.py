import asyncio

import aioschedule
import schedule
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup
from aiogram.utils.exceptions import ChatNotFound

from keyboards.inline.categories import categories_markup, categories_markup1
from keyboards.inline.products_from_cart import product_cb
from loader import dp, bot,db
from filters import IsAdmin, IsUser

catalog = 'Каталог'

cart = 'Корзинка'
delivery_status = 'Buyurtma holati'

settings = 'Katalogni sozlash'
orders = 'Buyurtmalar'
questions = 'Вопросы'

async def send_messange():
    ids = []
    ids2 = []
    fet = db.fetchall('SELECT cid FROM orders')
    a = len(fet)
    for x in range(0, a):
        id = fet[x][0]
        ids.append(id)
    for i in ids:
        if i not in ids2:
            ids2.append(i)
    r1=[]

    for r in ids2:
        r1.append(r)
    for r2 in r1:
        try:
            photo=open('handlers/user/elka-poezd-krasavica-igrushki.jpg','rb')
            await bot.send_photo(chat_id=r2,photo=photo,caption='Yangi yil bilan')
        except ChatNotFound:
            print(' ')
@dp.message_handler(IsAdmin(), commands='start')
async def admin_menu(message: Message):
    markup = ReplyKeyboardMarkup(selective=True,resize_keyboard=True)
    markup.add(settings)
    markup.add(questions, orders)

    await message.answer('Menu', reply_markup=markup)

@dp.callback_query_handler(IsUser(), text='home')
async def user_menu(query: CallbackQuery):









    await query.message.answer('Выберите раздел, чтобы вывести список товаров:',
                         reply_markup=categories_markup1())

@dp.message_handler(IsUser(), commands='start')
async def user_menu(message: Message):
    await message.answer('Выберите раздел, чтобы вывести список товаров:',
                            reply_markup=categories_markup1())



