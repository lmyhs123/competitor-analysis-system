# -*- coding: utf-8 -*-
"""
============================================================
 test_anthropic.py — Claude API 连通性测试（课件标准脚本）
============================================================
 用途：验证 .env 配置 / API 密钥 / 网络 / LangChain 集成 是否打通
 运行：python test_anthropic.py
"""
import os
import sys
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY", "")
if not api_key or "你的" in api_key or "your_key" in api_key.lower():
    print("[未配置] 请先在 .env 中填入真实 ANTHROPIC_API_KEY")
    sys.exit(1)

llm = ChatAnthropic(
    model=os.getenv("MODEL_HAIKU", "deepseek-v4-flash"),
    api_key=api_key,
    temperature=0.0,
    max_tokens=512,
    base_url=os.getenv("ANTHROPIC_BASE_URL") or None,  # 中转平台才需要
)

res = llm.invoke("简单测试：竞品降价10%会带来什么影响？")
print("API调用成功：", res.content)
