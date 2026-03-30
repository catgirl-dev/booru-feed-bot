import logging
from datetime import datetime, timedelta
from typing import List, Union, Optional

from peewee import Query

from database.models import UrlQueue, TagsArchive


def enqueue_urls() -> None:
    """Добавляет новые URL-адреса в очередь для каждого чата и каждого тега"""
    try:
        chat_ids: Query = TagsArchive.select(TagsArchive.chat_id).distinct()
        chat_id_list: list[int] = [int(chat_id.chat_id) for chat_id in chat_ids]

        for chat_id in chat_id_list:
            tags: list = list(TagsArchive.select().where(TagsArchive.chat_id == chat_id))

            for tag in tags:
                url: str = (f'https://kagamihara.donmai.us/posts.json?tags=date:>'
                            f'{str(tag.last_post_date)} {str(tag.tag)}')

                existing_url = UrlQueue.select().where(
                    UrlQueue.chat_id == chat_id,
                    UrlQueue.url == url
                ).first()

                if existing_url:
                    if existing_url.url != url:
                        existing_url.url = url
                        existing_url.status = 0
                        existing_url.save()
                        logging.info(f'URL обновлён для тега {tag.tag}: {url}')
                    elif existing_url.status == 1:
                        if hasattr(existing_url, 'updated_at'):
                            timeout = datetime.now() - timedelta(minutes=10)
                            if existing_url.updated_at < timeout:
                                existing_url.status = 0
                                existing_url.save()
                                logging.info(
                                    f'URL восстановлен для тега {tag.tag} (завис в обработке)')
                        else:
                            existing_url.status = 0
                            existing_url.save()
                            logging.info(f'URL восстановлен для тега {tag.tag} (сброс статуса)')
                    continue

                UrlQueue.create(chat_id=chat_id, url=url, tag=tag.tag, status=0)
                logging.info(f'Новый URL добавлен в очередь: {url}')

    except Exception as e:
        logging.error(f'Ошибка при добавлении URL в очередь: {e}')

def dequeue_and_get_urls(chat_id: int) -> Optional[List[UrlQueue]]:
    """Получает список URL-адресов из очереди для заданного чата и помечает их
    как "в обработке" (status=1)"""
    urls_from_db: list[UrlQueue] = list(UrlQueue.select().where(
        UrlQueue.chat_id == chat_id, UrlQueue.status == 0)
    )

    if not urls_from_db:
        return None

    url_list = [url.url for url in urls_from_db]

    # Меняем статус URL из очереди на "в обработке"
    UrlQueue.update(status=1).where(
        UrlQueue.chat_id == chat_id,
        UrlQueue.url.in_(url_list)
    ).execute()

    return urls_from_db
