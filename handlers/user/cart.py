import datetime
import logging

from aiogram.utils.exceptions import MessageNotModified
from geopy.geocoders import Nominatim
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, \
    InlineKeyboardButton, LabeledPrice, ShippingOption

import keybord
from keyboards.inline.categories import categories_markup, categories_markup1
from keyboards.inline.products_from_cart import product_markup, product_cb

from keyboards.default.markups import *
from aiogram.types.chat import ChatActions

from keybord import locations_buttons
from states import CheckoutState
from loader import dp, db, bot
from filters import IsUser
from .menu import cart
from aiogram.types import Message, ShippingOption, ShippingQuery, LabeledPrice, PreCheckoutQuery
from aiogram.types.message import ContentType

from .messages import MESSAGES
from data.config import PAYMENTS_TOKEN, item_url


@dp.callback_query_handler(IsUser(), text='Корзинка')
async def process_cart(query: CallbackQuery,state: FSMContext):


    cart_data = db.fetchall(
        'SELECT * FROM cart WHERE cid=?', (query.message.chat.id,))

    if len(cart_data) == 0:

            await query.message.answer('В твоей корзине ничего нет.')

    else:

        await bot.send_chat_action(query.message.chat.id, ChatActions.TYPING)
        async with state.proxy() as data:
            data['products'] = {}

        order_cost = 0

        for _, idx, count_in_cart in cart_data:
            count_in_cart=1
            product = db.fetchone('SELECT * FROM products WHERE idx=?', (idx,))

            if product == None:

                db.query('DELETE FROM cart WHERE idx=?', (idx,))

            else:
                _, title, body, image, price, _ = product
                order_cost += price

                async with state.proxy() as data:
                    data['products'][idx] = [title, price, count_in_cart]

                markup = product_markup(idx, count_in_cart)
                text = f"<b>{title}</b>\n\n{body}\n\nЦена: {price}so'm.\n Товар можно заказать не менее 10 штук"

                await query.message.answer_photo(photo=image,
                                           caption=text,
                                           reply_markup=markup)

        if order_cost != 0:
            markup = ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
            markup.add('📦 Оформить заказ')
            await query.message.answer('Перейти к оформлению?',
                                 reply_markup=markup)


@dp.callback_query_handler(IsUser(), product_cb.filter(action='count'))
@dp.callback_query_handler(IsUser(), product_cb.filter(action='increase'))
@dp.callback_query_handler(IsUser(), product_cb.filter(action='decrease'))
@dp.callback_query_handler(IsUser(), product_cb.filter(action='delete'))
@dp.callback_query_handler(IsUser(), product_cb.filter(action='dele'))
async def product_callback_handler(query: CallbackQuery, callback_data: dict, state: FSMContext):

    idx = callback_data['id']
    action = callback_data['action']

    if 'count' == action:

        async with state.proxy() as data:

            if 'products' not in data.keys():

                await process_cart(query=query,stat=state)

            else:

                await query.answer('Количество - ' + data['products'][idx][2])

    elif 'dele' == action:
        cart_data = db.fetchall(
            'SELECT * FROM cart WHERE cid=?', (query.message.chat.id,))

        cid = query.message.chat.id


        db.query('DELETE FROM cart WHERE cid=?', (cid,))



        await query.message.delete()
        await query.message.answer("Все товари из корзинку удалини",reply_markup=categories_markup1())
    else:
        try:
            async with state.proxy() as data:

                if 'products' not in data.keys():

                    await process_cart(query=query,state=state)


                else:

                    if 'increase' == action:

                        data['products'][idx][2] += 1

                    elif 'decrease' == action:



                        data['products'][idx][2] -= 1




                    elif 'delete' == action:

                        data['products'][idx][2] -= data['products'][idx][2]





                    count_in_cart = data['products'][idx][2]

                    if count_in_cart == 0:

                        db.query('''DELETE FROM cart
                        WHERE cid = ? AND idx = ?''', (query.message.chat.id, idx))

                        await query.message.delete()
                    else:

                        db.query('''UPDATE cart 
                        SET quantity = ? 
                        WHERE cid = ? AND idx = ?''', (count_in_cart, query.message.chat.id, idx))

                        await query.message.edit_reply_markup(product_markup(idx, count_in_cart))

        except MessageNotModified as exx:
           print(' ')
@dp.message_handler(IsUser(), text='📦 Оформить заказ')
async def process_checkout(message: Message, state: FSMContext):

    await CheckoutState.check_cart.set()
    await checkout(message, state)


async def checkout(message, state):
    answer = ''
    total_price = 0

    async with state.proxy() as data:

        for title, price, count_in_cart in data['products'].values():

            tp = count_in_cart * price
            answer += f'<b>{title}</b> * {count_in_cart}шт. = {tp}som\n'
            total_price += tp

    from keyboards.inline.products_from_catalog import check_markup
    await message.answer(f'{answer}\nОбщая сумма заказа  {total_price}som.',
                         reply_markup=ReplyKeyboardRemove())
    await message.answer(f' Если вы не хотите все покупвт вергнити и отмените заказы ',
                         reply_markup=check_markup())


@dp.message_handler(IsUser(), lambda message: message.text not in [all_right_message, back_message], state=CheckoutState.check_cart)
async def process_check_cart_invalid(message: Message):
    await message.reply('Такого варианта не было.')


@dp.callback_query_handler(IsUser(), text=back_message, state=CheckoutState.check_cart)
async def product_callback_handler(query: CallbackQuery,  state: FSMContext):
    await state.finish()
    print('111')
    await process_cart(query=query,state=state)


@dp.callback_query_handler(IsUser(), text=all_right_message, state=CheckoutState.check_cart)
async def process_check_cart_all_right(query: CallbackQuery, state: FSMContext):
    await CheckoutState.next()
    await query.message.answer("Нажмите кнопки ниже, чтобы отправить свой номер",
                         reply_markup=keybord.locations_buttons.keyboardcontakt)


@dp.message_handler(IsUser(), text=back_message, state=CheckoutState.name)
async def process_name_back(message: Message, state: FSMContext):
    await CheckoutState.check_cart.set()
    await checkout(message, state)


@dp.message_handler(IsUser(), state=CheckoutState.name,content_types=types.ContentType.CONTACT)
async def process_name(message: Message, state: FSMContext):
    contact = message.contact.phone_number
    async with state.proxy() as data:

        data['name'] = contact



        await CheckoutState.next()
        await message.answer(f"{message.from_user.full_name}.\n"
                             f"Вибирайте тип оплати",reply_markup=nalcar())

@dp.message_handler(IsUser(),text="Картой", state=CheckoutState.address)
async def process_name(message: Message, state: FSMContext):

        PRICES = [
            LabeledPrice(label='Ноутбук', amount=1000000000),
            LabeledPrice(label='Прочная упаковка', amount=1000000000)
        ]

        SUPERSPEED_SHIPPING_OPTION = ShippingOption(
            id='superspeed',
            title='Супер быстрая!'
        ).add(LabeledPrice('Лично в руки!', 1000000000))

        POST_SHIPPING_OPTION = ShippingOption(
            id='post',
            title='Почта России'
        )

        POST_SHIPPING_OPTION.add(LabeledPrice('Кортонная коробка', 1000000000))
        POST_SHIPPING_OPTION.add(LabeledPrice('Срочное отправление!', 1000000000))

        PICKUP_SHIPPING_OPTION = ShippingOption(
            id='pickup',
            title='Самовывоз'
        )
        PICKUP_SHIPPING_OPTION.add(LabeledPrice('Самовывоз в Сантк-Петербурге', 1000000000))
        print(1)
        await bot.send_invoice(message.chat.id,
                               title="maxsulot",
                               description="maxsulotlar",
                               provider_token='398062629:TEST:999999999_F91D8F69C042267444B74CC0B3C747757EB0E065',
                               currency='uzs',
                               photo_url='https://images.unsplash.com/photo-1603302576837-37561b2e2302?ixlib=rb-1.2.1&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=1468&q=80',
                               photo_height=512,
                               photo_width=512,
                               photo_size=512,
                               need_email=True,
                               need_phone_number=True,
                               is_flexible=True,
                               prices=PRICES,
                               start_parameter='example',
                               payload='some_invoice')


@dp.message_handler(IsUser(), text=back_message, state=CheckoutState.address)
async def process_address_back(message: Message, state: FSMContext):

    async with state.proxy() as data:

        await message.answer('Изменить имя с <b>' + data['name'] + '</b>?',
                             reply_markup=back_markup())

    await CheckoutState.name.set()


@dp.message_handler(IsUser(), state=CheckoutState.address)
async def process_address(message: Message, state: FSMContext):

    async with state.proxy() as data:
        data['address'] = message.text


    await message.answer(

        f"Нажмите кнопку внизу чтобы отправить ваша местоположение",
        reply_markup=locations_buttons.keyboard
    )
    await CheckoutState.q3.set()


@dp.message_handler(IsUser(), state=CheckoutState.q3, content_types=types.ContentTypes.LOCATION)

async def location(message: Message,state:FSMContext):

    global choose
    location1 = message.location

    lat = location1.latitude
    lon = location1.longitude
    URL = "http://maps.google.com/maps?q={lat},{lon}"

    map_local = URL.format(lat=lat, lon=lon)





    data = await state.get_data()
    answer1 = data.get("name")
    answer2 = data.get("address")
    cart_data = db.fetchall(
        'SELECT idx FROM cart WHERE cid=?', (message.chat.id,))
    maxsulotlar={'maxsulot':[],'maxsulotning soni':[]}

    answer = ''
    total_price = 0
    for x in cart_data:

        quantity = db.fetchone(
            'SELECT quantity FROM cart WHERE cid=? and idx=?', (message.chat.id,x[0],))
        prodyct_name = db.fetchone(
            'SELECT title FROM products WHERE idx=?', (x[0],))
        maxsulotlar['maxsulot'].append(prodyct_name[0])
        maxsulotlar['maxsulotning soni'].append(quantity[0])
    async with state.proxy() as data:

        for title, price, count_in_cart in data['products'].values():

            tp = count_in_cart * price
            answer += f'<b>{title}</b> * {count_in_cart}шт. = {tp}som\n'
            total_price += tp

    zakazkuni=datetime.datetime.now().strftime('%d:%m:%Y')
    zakazvaqti=datetime.datetime.now().strftime('%X')

    await bot.send_message(chat_id=-10000000001668368433,
                           text=f"Ден заказа {zakazkuni}\n\n Время заказа {zakazvaqti}\n\n Тип оплати:\n\n{answer2} имя: {message.from_user.full_name}  \n\ntelefon raqami:\n\n{answer1}\n\n locatsiyasi:\n\n {map_local}  \n\n\n\n"
                                f"Buyurtma qilgan maxsulotlar\n {answer}\nОбщая сумма заказа: {total_price}som.")
    await CheckoutState.confirm.set()
    logging.info('Deal was made.')

    async with state.proxy() as data:

        cid = message.chat.id
        products = [idx + '=' + str(quantity)
                    for idx, quantity in db.fetchall('''SELECT idx, quantity FROM cart
        WHERE cid=?''', (cid,))]  # idx=quantity

        db.query('INSERT INTO orders VALUES (?, ?, ?, ?)',
                 (cid, data['name'], data['address'], ' '.join(products)))

        db.query('DELETE FROM cart WHERE cid=?', (cid,))
        await message.answer('Заказ отпрален',reply_markup=ReplyKeyboardRemove())
        await message.answer('Если хотите заказать еще нажмите кнопку внизу',reply_markup=categories_markup1())
    await state.finish()

@dp.message_handler(IsUser(), text=confirm_message, state=CheckoutState.confirm)
async def process_confirm(message: Message, state: FSMContext):

    enough_money = True  # enough money on the balance sheet
    markup = ReplyKeyboardRemove()

    if enough_money:

        logging.info('Deal was made.')

        async with state.proxy() as data:

            cid = message.chat.id
            products = [idx + '=' + str(quantity)
                        for idx, quantity in db.fetchall('''SELECT idx, quantity FROM cart
            WHERE cid=?''', (cid,))]  # idx=quantity

            db.query('INSERT INTO orders VALUES (?, ?, ?, ?)',
                     (cid, data['name'], data['address'], ' '.join(products)))

            db.query('DELETE FROM cart WHERE cid=?', (cid,))

            await message.answer('Ок! Ваш заказ уже в пути 🚀\nИмя: <b>' + data['name'] + '</b>\nАдрес: <b>' + data[
                'address'] + '</b>',
                                 reply_markup=markup)
    else:

        await message.answer('У вас недостаточно денег на счете. Пополните баланс!',
                             reply_markup=markup)

    await state.finish()