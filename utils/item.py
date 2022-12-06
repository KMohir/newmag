from aiogram import types
async def set(dp):
    await dp.bot.set_my_commands(
        [types.BotCommand("start", "Через это вы сможете запустить бота")]

)