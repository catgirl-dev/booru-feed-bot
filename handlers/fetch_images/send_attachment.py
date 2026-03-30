import logging
import asyncio
from enum import Enum
from typing import Union

from aiogram.exceptions import TelegramRetryAfter, TelegramBadRequest
from aiogram.types import InputFile

from configuration.environment import bot
from database.models import CensorStatus


# TODO: добавить обработку события удаления бота из чата
class AttachmentType(Enum):
    """Типы медиафайлов"""
    VIDEO = 1
    GIF = 2
    PHOTO = 3


class SendAttachCommand:
    """Команда для отправки медиафайла в чат """
    def __init__(self, attachment_type: AttachmentType, file: Union[InputFile, str], has_spoiler: bool, chat_id: any):
        self.attachmentType = attachment_type
        self.file = file
        self.has_spoiler = has_spoiler
        self.chat_id = chat_id


class CensorLevel(Enum):
    """Статусы цензуры. 0 — выключить, 1 — включить, 2 — не присылать 18+"""
    NO_CENSOR = 0
    PARTIAL_CENSOR = 1
    FULL_CENSOR = 2


def get_send_command(post: any, chat_id: any) -> Union[SendAttachCommand, None]:
    """Проверяет статус цензуры и формирует команду для отправки медиафайла"""
    try:
        censor_status_found = CensorStatus.select().where(CensorStatus.chat_id == chat_id).first()
    except Exception as e:
        logging.error(f"Ошибка при попытке получить статус цензуры{e}")
        return None

    if not censor_status_found:
        logging.error('Не получен статус цензуры для чата')
        return None

    current_censor_status = CensorLevel(censor_status_found.status) # привожу к Enum

    if post['file_ext'] == 'gif':
        att_type = AttachmentType.GIF
    elif post['file_ext'] in ['mp4', 'webm', 'ogv']:
        att_type = AttachmentType.VIDEO
    elif post['file_ext'] in ['png', 'jpg', 'jpeg']:
        att_type = AttachmentType.PHOTO
    else:
        logging.info(f"Некорректный формат: {post['file_ext']}")
        return None

    # Questionable (q), Explicit (e), Sensitive (s)
    censored_ratings = {'q', 'e', 's'}
    has_spoiler: bool = False

    if current_censor_status == CensorLevel.PARTIAL_CENSOR:
        has_spoiler = post['rating'] in censored_ratings
    elif current_censor_status == CensorLevel.NO_CENSOR:
        has_spoiler = False
    elif current_censor_status == CensorLevel.FULL_CENSOR:
        if post['rating'] in censored_ratings:
            logging.info("Пост 18+ не будет отправлен")
            return None
        has_spoiler = False

    return SendAttachCommand(att_type, post['file_url'], has_spoiler, chat_id)


async def send_attachment(command: SendAttachCommand, max_retries: int = 3):
    """
    Отправляет медиафайл по типу вложения
    с обработкой flood control и ретраями
    """
    await asyncio.sleep(0.5)

    for attempt in range(max_retries):
        try:
            match command.attachmentType:
                case AttachmentType.VIDEO:
                    await bot.send_video(
                        chat_id=command.chat_id,
                        video=command.file,
                        has_spoiler=command.has_spoiler,
                    )
                case AttachmentType.GIF:
                    await bot.send_animation(
                        chat_id=command.chat_id,
                        animation=command.file,
                        has_spoiler=command.has_spoiler,
                    )
                case AttachmentType.PHOTO:
                    await bot.send_photo(
                        chat_id=command.chat_id,
                        photo=command.file,
                        has_spoiler=command.has_spoiler,
                    )
            await asyncio.sleep(1.0)
            return

        except TelegramRetryAfter as e:
            wait_time = e.retry_after
            logging.warning(
                f"Flood control! Чат {command.chat_id}: ждём {wait_time} секунд "
                f"(попытка {attempt + 1}/{max_retries})"
            )
            await asyncio.sleep(wait_time + 0.5)
            continue

        except TelegramBadRequest as e:
            error_msg = str(e).lower()

            if "wrong type of the web page content" in error_msg:
                logging.error(
                    f"Неверный тип контента для чата {command.chat_id}: {command.file}"
                )
                return

            if "kicked" in error_msg or "blocked" in error_msg:
                logging.error(f"Бот был удалён из чата {command.chat_id}. Очищаем данные...")
                # добавить обработку события
                return

            elif "failed to get http url content" in error_msg:
                logging.error(
                    f"Не удалось загрузить контент для чата {command.chat_id}: {command.file}. "
                    f"Файл может быть удалён или недоступен."
                )
                return
            else:
                logging.error(f"BadRequest при отправке в чат {command.chat_id}: {e}")

            return

        except Exception as e:
            logging.error(f"Неожиданная ошибка при отправке в чат {command.chat_id}: {e}")
            if attempt == max_retries - 1:
                return
            wait_time = 2 ** attempt
            logging.info(f"Повторная попытка через {wait_time} секунд")
            await asyncio.sleep(wait_time)

    logging.error(f"Не удалось отправить медиа после {max_retries} попыток")