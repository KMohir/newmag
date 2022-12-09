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
help_message = '''
Отправьте команду /buy, чтобы перейти к покупке.
Узнать правила можно воспользовавшись командой /terms.
'''

start_message = 'Привет! Сейчас ты увидишь работу платежей в Telegram!\n' + help_message

terms = '''\
Правила!
'''

item_title = 'Ноутбук'
item_description = '''\
Купить ноутбук крутой честно правда
'''

AU_error = '''\
В данную страну доставка не оформляется. Сорри
'''

successful_payment = '''
Платеж на сумму `{total_amount} {currency}` совершен успешно!
'''


MESSAGES = {
    'start': start_message,
    'help': help_message,
    'terms': terms,
    'item_title': item_title,
    'item_description': item_description,
    'AU_error': AU_error,
    'successful_payment': successful_payment,
}




@dp.callback_query_handler(IsUser(), text='Корзинка')
async def process_cart(query: CallbackQuery,state: FSMContext):


    cart_data = db.fetchall(
        'SELECT * FROM cart WHERE cid=?', (query.message.chat.id,))

    if len(cart_data) == 0:

            await query.message.answer('Вы ничего не добавили в корзину.')

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


async def checkout(message, state:FSMContext):
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
    answer = ''
    total_price = 0
    PRICES=[]
    async with state.proxy() as data:
        for title, price, count_in_cart in data['products'].values():
            PRICES.append(LabeledPrice(label=str(title), amount=price*count_in_cart*100))
        global SUPERSPEED_SHIPPING_OPTION
        global POST_SHIPPING_OPTION
        POST_SHIPPING_OPTION = ShippingOption(
            id='post',
            title='Почта России'
        )

        POST_SHIPPING_OPTION.add(LabeledPrice('Кортонная коробка', 1133351))
        POST_SHIPPING_OPTION.add(LabeledPrice('Срочное отправление!', 1133351))



        SUPERSPEED_SHIPPING_OPTION = ShippingOption(
            id='superspeed',
            title='Супер быстрая!'
        ).add(LabeledPrice('Лично в руки!', 1133351))


        await bot.send_invoice(message.chat.id,
                               title="maxsulot",
                               description="maxsulotlar",
                               provider_token='398062629:TEST:999999999_F91D8F69C042267444B74CC0B3C747757EB0E065',
                               currency='uzs',
                               photo_url='https://cdnn21.img.ria.ru/images/148680/92/1486809213_272:0:4627:3266_1920x0_80_0_0_ce9b180145cc88837a3e93425261ecdc.jpg',
                               photo_height=512,
                               photo_width=512,
                               photo_size=512,
                               need_email=True,
                               need_phone_number=True,
                               is_flexible=True,
                               prices=PRICES,
                               start_parameter='example',
                               payload='some_invoice')
@dp.shipping_query_handler(lambda q: True)
async def shipping_process(shipping_query: ShippingQuery):
    if shipping_query.shipping_address.country_code == 'UZ':
        return await bot.answer_shipping_query(
            shipping_query.id,
            ok=False,
            error_message=MESSAGES['AU_error']
        )

    shipping_options = [SUPERSPEED_SHIPPING_OPTION]
    if shipping_query.shipping_address.country_code=="UZ":
        shipping_options.append(POST_SHIPPING_OPTION)
    await bot.answer_shipping_query(
        shipping_query.id,
        ok=True,
        shipping_options=shipping_options
    )


@dp.pre_checkout_query_handler(lambda q: True)
async def checkout_process(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message_handler(content_types=ContentType.SUCCESSFUL_PAYMENT, state=CheckoutState.check_cart)
async def successful_payment(message: Message):
    await bot.send_message(
        message.chat.id,
        MESSAGES['successful_payment'].format(total_amount=message.successful_payment.total_amount,
                                              currency=message.successful_payment.currency)
    )
    await CheckoutState.next()
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
    cidnumber = message.message_id
    await bot.send_message(chat_id=-1001668368433,
                           text=f"id : {cidnumber} \n\nДен заказа {zakazkuni}\n\n Время заказа {zakazvaqti}\n\n Тип оплати:\n\n{answer2}\n\n Имя:\n\n{message.from_user.full_name}  \n\ntelefon raqami:\n\n{answer1}\n\n locatsiyasi:\n\n {map_local}  \n\n"
                                f"Buyurtma qilgan maxsulotlar\n {answer}\nОбщая сумма заказа: {total_price}som.")
    await CheckoutState.confirm.set()
    logging.info('Deal was made.')

    async with state.proxy() as data:

        cid = message.chat.id
        products = [idx + '=' + str(quantity)
                    for idx, quantity in db.fetchall('''SELECT idx, quantity FROM cart
        WHERE cid=?''', (cid,))]  # idx=quantity

        db.query('INSERT INTO orders VALUES (?, ?, ?, ?)',
                 (cid, data['name'], data['address'], cidnumber))

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
                     (cid, data['name'], data['address'],cid))

            db.query('DELETE FROM cart WHERE cid=?', (cid,))

            await message.answer('Ок! Ваш заказ уже в пути \nИмя: <b>' + data['name'] + '</b>\nАдрес: <b>' + data[
                'address'] + '</b>',
                                 reply_markup=markup)
    else:

        await message.answer('У вас недостаточно денег на счете. Пополните баланс!',
                             reply_markup=markup)

    await state.finish()