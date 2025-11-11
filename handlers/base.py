from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram import F

from texts import help_msg
from configuration.environment import bot


base: Router = Router()


@base.message(F.new_chat_members)
async def on_bot_added(message: Message):
    """Приветственное сообщение бота при добавлении его в чат"""
    for member in message.new_chat_members:
        if member.id == (await bot.me()).id:
            await message.reply(
                help_msg.help_msg,
                parse_mode='Markdown',
                disable_web_page_preview=True)


@base.message(Command('ping'))
async def ping(message: Message):
    """Ответ бота на команду /ping"""
    await message.reply('pong!')


@base.message(Command('help'))
async def help_command(message: Message):
    """Ответ бота на команду /help"""
    await message.reply(
        help_msg.help_msg,
        parse_mode='Markdown',
        disable_web_page_preview=True)


@base.message(Command('start'))
async def start(message: Message):
    """Ответ бота на команду /start"""
    await message.reply(
        help_msg.help_msg,
        parse_mode='Markdown',
        disable_web_page_preview=True)