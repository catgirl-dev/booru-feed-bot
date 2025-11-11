from aiogram import Router

from database.models import db, TagsArchive, IntervalConfig, PostIds, CensorStatus, UrlQueue

lifecycle: Router = Router()


@lifecycle.startup()
async def on_startup():
    """Выполняется при запуске приложения"""
    db.connect()
    db.create_tables(
        [TagsArchive,
         IntervalConfig,
         PostIds,
         CensorStatus,
         UrlQueue]
    )


@lifecycle.shutdown()
async def on_shutdown():
    """Выполняется при завершении работы приложения"""
    db.close()
