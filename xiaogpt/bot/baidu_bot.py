from __future__ import annotations

import dataclasses
from typing import ClassVar

import httpx
import openai
from rich import print

from xiaogpt.bot.base_bot import BaseBot, ChatHistoryMixin
from xiaogpt.utils import split_sentences

import requests
import json

@dataclasses.dataclass
class BaiduBot(ChatHistoryMixin, BaseBot):
    name: ClassVar[str] = "百度"
    api_key: str | None = None
    secret_key: str | None = None
    proxy: str | None = None

    history: list[tuple[str, str]] = dataclasses.field(default_factory=list, init=False)

    def get_access_token(self):
        """
        使用 AK，SK 生成鉴权签名（Access Token）
        :return: access_token，或是None(如果错误)
        """
        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {"grant_type": "client_credentials", "client_id": self.api_key, "client_secret": self.secret_key}
        return str(requests.post(url, params=params).json().get("access_token"))
    
    async def ask_baidu_msg(self, messages, sess, stream=False):
        token = self.get_access_token()
        if token == None:
            print("get baidu access token failed")
            return "获取百度Token失败"
        
        url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/eb-instant?access_token=" + token
        
        payload = json.dumps({
            "messages": messages,
            "stream": stream
        })
        headers = {
            'Content-Type': 'application/json'
        }
        
        response = httpx.request("POST", url, headers=headers, data=payload)
        
        text = ""
        if stream == True:
            for line in response.iter_lines():
                print(line)
        else:
            json_res = response.json()
            print("json_res=%s", json_res)
            text = json_res["result"]
            print("text=%s", text)

        return text

    @classmethod
    def from_config(cls, config):
        return cls(
            api_key=config.baidu_apikey,
            secret_key=config.baidu_secret,
        )

    async def ask(self, query, **options):
        ms = self.get_messages()
        ms.append({"role": "user", "content": f"{query}"})
        httpx_kwargs = {}
        if self.proxy:
            httpx_kwargs["proxies"] = self.proxy
        async with httpx.AsyncClient(trust_env=True, **httpx_kwargs) as sess:
            try:
                message = await self.ask_baidu_msg(ms, sess)
            except Exception as e:
                print (str(e))
                return ""

            self.add_message(query, message)
            print(message)
            return message

    async def ask_stream(self, query, **options):
        ms = self.get_messages()
        ms.append({"role": "user", "content": f"{query}"})
        kwargs = {**self.default_options, **options}
        httpx_kwargs = {}
        if self.proxy:
            httpx_kwargs["proxies"] = self.proxy
        async with httpx.AsyncClient(trust_env=True, **httpx_kwargs) as sess:
            try:
                message = await self.ask_baidu_msg(ms, sess, stream=True)
            except Exception as e:
                print(str(e))
                return
            self.add_message(message)
            print(message)
            return message