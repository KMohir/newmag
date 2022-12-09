
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, CallbackQuery
from keyboards.default.markups import all_right_message, cancel_message, submit_markup
from aiogram.types import Message

from keyboards.inline.categories import categories_markup, categories_markup1
from states import SosState
from filters import IsUser
from loader import dp, db, bot


@dp.callback_query_handler(text='Вопросы')
async def cmd_sos(query: CallbackQuery):
    await SosState.question.set()
    await query.message.answer('В чем суть проблемы? Опишите как можно более подробно, и администратор обязательно ответит вам.', reply_markup=ReplyKeyboardRemove())



@dp.message_handler(state=SosState.question)
async def process_question(message: Message, state: FSMContext):
    async with state.proxy() as data:
        data['question'] = message.text

    await message.answer('Убедитесь, что все верно.', reply_markup=submit_markup())
    await SosState.next()


@dp.message_handler(lambda message: message.text not in [cancel_message, all_right_message], state=SosState.submit)
async def process_price_invalid(message: Message):
    await message.answer('Такого варианта не было.')


@dp.message_handler(text=cancel_message, state=SosState.submit)
async def process_cancel(message: Message, state: FSMContext):
    await message.answer('Отменено!', reply_markup=ReplyKeyboardRemove())
    await state.finish()


@dp.message_handler(text=all_right_message, state=SosState.submit)
async def process_submit(message: Message, state: FSMContext):

    cid = message.chat.id

    if db.fetchone('SELECT * FROM questions WHERE cid=?', (cid,)) == None:

        async with state.proxy() as data:
            db.query('INSERT INTO questions VALUES (?, ?)',
                     (cid, data['question']))
        await state.finish()
        await message.answer('Отправлено!', reply_markup=ReplyKeyboardRemove())
        await message.answer('Выберите раздел, чтобы вывести список товаров:',
                                   reply_markup=categories_markup1())

    else:

        await message.answer('Превышен лимит на количество задаваемых вопросов.', reply_markup=ReplyKeyboardRemove())
        await message.answer('Выберите раздел, чтобы вывести список товаров:',
                                   reply_markup=categories_markup1())
        await state.finish()

    await state.finish()
