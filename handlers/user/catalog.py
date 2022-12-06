

import logging
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from keyboards.inline.categories import categories_markup, category_cb, cat_cb, categories_markup1
from keyboards.inline.products_from_catalog import product_markup, product_cb
from aiogram.utils.callback_data import CallbackData
from aiogram.types.chat import ChatActions
from loader import dp, db, bot
from .menu import catalog
from filters import IsUser
add_product = '➕ Добавить товар'



@dp.message_handler(IsUser(), text=catalog)
async def process_catalog(message: Message):
    await message.answer('Выберите ',
                         reply_markup=categories_markup1())






@dp.callback_query_handler(IsUser(), category_cb.filter(action='view'))
async def category_callback_handler(query: CallbackQuery, callback_data: dict):
    idx=callback_data['id']
    photos=db.fetchall('''SELECT * FROM categori WHERE idx=?''',
                      (idx,))
    products = db.fetchall('''SELECT * FROM categories cat
        WHERE cat.tag = (SELECT title FROM categori WHERE idx=?)''',
                          (idx,))

    for title,idx,photo in photos:
        await bot.send_photo(chat_id=query.message.chat.id,photo=photo,caption='Выберите раздел, чтобы вывести список товаров:',
                             reply_markup=categories_markup(products))


@dp.callback_query_handler(IsUser(), product_cb.filter(action='view'))
async def category_callback_handler(query: CallbackQuery, callback_data: dict):

    products = db.fetchall('''SELECT * FROM products product
    WHERE product.tag = (SELECT title FROM categories WHERE idx=?) 
    AND product.idx NOT IN (SELECT idx FROM cart WHERE cid = ?)''',
                           (callback_data['id'], query.message.chat.id))

    await query.answer('Все доступные товары.')
    await show_products(query.message, products)




@dp.callback_query_handler(IsUser(), product_cb.filter(action='add'))
async def add_product_callback_handler(query: CallbackQuery, callback_data: dict):

    db.query('INSERT INTO cart VALUES (?, ?, 1)',
             (query.message.chat.id, callback_data['id']))

    await query.answer('Товар добавлен в корзину!')
    await query.message.delete()


async def show_products(m, products):

    if len(products) == 0:

        await m.answer('Все продукты добавили в корзинку',reply_markup=categories_markup1())

    else:

        await bot.send_chat_action(m.chat.id, ChatActions.TYPING)

        for idx, title, body, image, price, _ in products:

            markup = product_markup(idx, price)
            text = f'<b>{title}</b>\n\n{body}'

            await m.answer_photo(photo=image,
                                 caption=text,
                                 reply_markup=markup)
async def show_products1(m, products, category_idx):
    markup = InlineKeyboardMarkup()
    products = db.fetchall('''SELECT * FROM categories cat
        WHERE cat.tag = (SELECT title FROM categori WHERE idx=?)''',
                           (category_idx,))
    for idx, title , tag in db.fetchall('''SELECT * FROM categories cat
        WHERE cat.tag = (SELECT title FROM categori WHERE idx=?)''',
                           (category_idx,)):
        markup.add(InlineKeyboardButton(
            title, callback_data=category_cb.new(id=idx, action='view')))

    markup.add(InlineKeyboardButton(
        add_product, callback_data='➕ Добавить товар'))

    await m.answer('Настройка категорий:', reply_markup=markup)
