import os

import injector
from contextvar_request_scope import request_scope
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from zoe_injector_persistence import DatabaseModule

from main.config import ZoeConfig


class ThreePartServiceClass:
    async def say_hello(self):
        print('ThreePartServiceClass: say_hello')
        return 'hello'


class DemoModule(injector.Module):

    @injector.singleton
    @injector.provider
    def get_config(self) -> ZoeConfig:
        return {'whatever': self.whatever}


def setup_dependency_injection(
        settings: dict,
) -> injector.Injector:
    modules = []
    # database_module = DatabaseModule(
    #     dsn='mysql+aiomysql://root:q123q123@localhost:5080/invoice',
    #     pool_size=5,
    #     pool_max_overflow=50,
    #     pool_recycle=3600,
    #     pool_pre_ping=True,
    # )
    # modules.append(database_module)

    _injector = injector.Injector(modules, auto_bind=False)

    return _injector
