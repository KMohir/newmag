from aiogram.dispatcher.filters.state import StatesGroup, State

class Categ(StatesGroup):
    title = State()
    confirm = State()

class CategoryState(StatesGroup):
    title = State()
    photo = State()
    confirm = State()

class ProductState(StatesGroup):
    title = State()
    body = State()
    image = State()
    price = State()
    confirm = State()