import asyncio
import dataclasses
import hashlib
import json
import os
from typing import Any

import aiohttp as aiohttp


class OneTrueConfig:

    def __init__(self):
        self._config = {}

    def get(self, key: str) -> Any:
        return self._config.get(key)

    def __getitem__(self, key: str) -> Any:
        return self.get(key)

    def update_all(self, config: dict):
        self._config.update(config)


class NacosRequestor:
    async def get(self, url: str, params: dict) -> bytes:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                return await resp.content.read()

    async def post(self, url: str, data: dict, headers: dict) -> bytes:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, headers=headers) as resp:
                return await resp.content.read()


@dataclasses.dataclass(frozen=True)
class NacosKey:
    namespace: str
    group: str
    data_id: str


class NacosConfigManager:

    WORD_SEPARATOR = '\x02'
    LINE_SEPARATOR = '\x01'

    def __init__(
            self,
            requestor: NacosRequestor,
    ):
        self.nacos_service_addr = os.getenv('NACOS_SERVICE_ADDR', 'http://localhost:8848')
        self.nacos_namespace = os.getenv('NACOS_NAMESPACE', 'f8c9a405-0b81-4878-8cc7-f7dc75de658f')
        self.nacos_data_id = os.getenv('NACOS_DATA_ID', 'fastapi')
        self.nacos_group = os.getenv('NACOS_GROUP', 'fastapi')
        self.nacos_username = os.getenv('NACOS_USERNAME', 'nacos')
        self.nacos_password = os.getenv('NACOS_PASSWORD', 'nacos')
        self.requestor = requestor

        self.last_config_hash = None

    def _update_config_hash(self, config_bytes: bytes):
        config_hash = hashlib.md5(config_bytes).hexdigest()
        self.last_config_hash = config_hash

    async def get_config(self) -> bytes:
        url = f'{self.nacos_service_addr}/nacos/v1/cs/configs'
        params = {
            'dataId': self.nacos_data_id,
            'group': self.nacos_group,
            'tenant': self.nacos_namespace,
        }
        config_bytes = await self.requestor.get(url, params)
        self._update_config_hash(config_bytes)
        return config_bytes

    async def listen_config(self) -> dict:
        url = f'{self.nacos_service_addr}/nacos/v1/cs/configs/listener'
        listening_configs = self.WORD_SEPARATOR.join([
            self.nacos_data_id,
            self.nacos_group,
            self.last_config_hash or '',
            self.nacos_namespace,
        ])
        params = {
            "Listening-Configs": listening_configs + self.LINE_SEPARATOR,
        }
        headers = {
            "Long-Pulling-Timeout": "100",
        }
        wtf = await self.requestor.post(url, params, headers)
        return wtf


if __name__ == '__main__':
    async def main():
        nacos = NacosConfigManager(NacosRequestor())
        from pprint import pprint
        counter = 0
        while True:
            print(f'{counter}', end=': ')
            # pprint(await nacos.get_config())
            pprint(await nacos.listen_config())
            counter += 1

    asyncio.run(main())
