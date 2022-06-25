import asyncio
import dataclasses
import hashlib
import json
import logging
import os
from typing import Any, Dict, Tuple, List

import aiohttp as aiohttp

logger = logging.getLogger(__name__)


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
                request_response = await resp.content.read()
                logger.debug(f'NacosRequestor[{id(self)}] '
                             f'Get: url={url}, params={params}, request_response={request_response}')
                return request_response

    async def post(self, url: str, data: dict, headers: dict) -> bytes:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, headers=headers) as resp:
                response_content = await resp.content.read()
                logger.debug(f'NacosRequestor [{id(self)}]'
                             f'Post: url={url}, data={data}, headers={headers}, '
                             f'response_content={response_content}')
                return response_content


_WORD_SEPARATOR = '\x02'
_LINE_SEPARATOR = '\x01'


@dataclasses.dataclass(frozen=True)
class NacosConfig:
    address: str
    username: str
    password: str

    long_pulling_timeout_ms: int = 100  # milliseconds


@dataclasses.dataclass
class NacosKey:
    namespace: str
    group: str
    data_id: str

    @classmethod
    def from_listening_config(cls, config: bytes) -> 'NacosKey':
        config_str = config.decode('utf-8')
        data_id, group, tenant = config_str.split('%02')
        return cls(tenant, group, data_id)

    def __eq__(self, other):
        return self.namespace == other.namespace and self.group == other.group and self.data_id == other.data_id

    def __hash__(self):
        return hash((self.namespace, self.group, self.data_id))


@dataclasses.dataclass
class NacosValue:
    key: NacosKey

    current_config: bytes = None
    current_version_md5: str = ''

    def update(self, new_config: bytes):
        self.current_config = new_config
        self.current_version_md5 = hashlib.md5(new_config).hexdigest()

    def as_listening_config(self) -> str:
        return _WORD_SEPARATOR.join([
            self.key.data_id,
            self.key.group,
            self.current_version_md5,
            self.key.namespace,
        ])

    def as_key(self) -> str:
        return _WORD_SEPARATOR.join([self.key.data_id, self.key.group, self.key.namespace])

    def is_key_equal(self, data_id: str, group: str, namespace: str) -> bool:
        key = self.key
        return key.data_id == data_id and key.group == group and key.namespace == namespace


class NacosConfigManager:

    def __init__(
            self,
            nacos_config: NacosConfig,
            requestor: NacosRequestor,
            nacos_keys: List[NacosKey],
    ):
        self.requestor = requestor

        self.nacos_config = nacos_config
        self.service_addr = nacos_config.address
        self.username = nacos_config.username
        self.password = nacos_config.password

        self.keys: Dict[NacosKey, NacosValue] = {
            key: NacosValue(key) for key in nacos_keys
        }

        # urls
        self.get_config_url = f'{self.service_addr}/nacos/v1/cs/configs'
        self.listen_config_url = f'{self.service_addr}/nacos/v1/cs/configs/listener'

    async def _get_config(self, nacos_key: NacosKey) -> bytes:
        params = {
            'dataId': nacos_key.data_id,
            'group': nacos_key.group,
            'tenant': nacos_key.namespace,
        }
        config_bytes = await self.requestor.get(self.get_config_url, params)
        return config_bytes

    async def _listen_config(self) -> List[NacosKey]:
        params = {
            "Listening-Configs": _LINE_SEPARATOR.join([
                key.as_listening_config() for key in self.keys.values()
            ]) + _LINE_SEPARATOR,
        }
        headers = {
            "Long-Pulling-Timeout": str(self.nacos_config.long_pulling_timeout_ms),
        }
        updated = await self.requestor.post(self.listen_config_url, params, headers)
        updated = updated.strip().strip(b'%01')
        if not updated:
            return []
        updated = updated.split(b'%01')
        return [NacosKey.from_listening_config(config) for config in updated]

    async def run_listen_config(self, callback):
        for key, value in self.keys.items():
            new_config_content = await self._get_config(key)
            value.update(new_config_content)

        while True:
            updated_keys = await self._listen_config()
            for key in updated_keys:
                new_config_content = await self._get_config(key)
                self.keys[key].update(new_config_content)
                print(f'updated {key} {self.keys[key].current_version_md5}')
                # await callback(updated_keys)


if __name__ == '__main__':
    one_nacos_key = NacosKey(
        namespace="f8c9a405-0b81-4878-8cc7-f7dc75de658f",
        # namespace="dev",
        group="fastapi",
        data_id="fastapi",
    )

    another_nacos_key = NacosKey(
        namespace="f8c9a405-0b81-4878-8cc7-f7dc75de658f",
        group="demo",
        data_id="demo",
    )

    test_nacos_config = NacosConfig(
        address="http://localhost:8848",
        username="nacos",
        password="nacos",
    )


    async def main():
        nacos = NacosConfigManager(
            test_nacos_config,
            NacosRequestor(),
            [one_nacos_key, another_nacos_key],
        )
        from pprint import pprint
        await nacos.run_listen_config(lambda x: pprint(x))


    asyncio.run(main())
