# -*- coding: utf-8 -*-
"""
============================================================
 Claude API + LangChain 连通性测试
------------------------------------------------------------
 用途：验证 环境变量 / API 密钥 / 网络 / LangChain 集成 是否正常
 运行：python test_claude.py
 退出码：0 成功 / 1 配置错误 / 2 网络或 API 错误
============================================================
"""
import os
import sys
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic


def load_config():
    """加载 .env 并校验配置完整性"""
    load_dotenv()

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    base_url = os.getenv("ANTHROPIC_BASE_URL", "").strip()

    # 1) 密钥必须配置且不能是占位符
    if not api_key:
        print("[ERROR] 未检测到 ANTHROPIC_API_KEY")
        print("   请在项目根目录 .env 文件中填写：ANTHROPIC_API_KEY=sk-你的DeepSeek密钥")
        sys.exit(1)
    if "你的" in api_key or "your_key" in api_key.lower():
        print("[ERROR] ANTHROPIC_API_KEY 仍是占位符，请在 .env 中替换为真实密钥")
        sys.exit(1)

    # 2) 模型名（DeepSeek 统一用 deepseek-v4-flash，可通过 ANTHROPIC_MODEL 覆盖）
    model = os.getenv("ANTHROPIC_MODEL", "deepseek-v4-flash").strip()

    # 3) 打印当前配置（脱敏密钥）
    masked = api_key[:10] + "*" * (len(api_key) - 14) + api_key[-4:]
    print("=" * 60)
    print("配置信息")
    print("=" * 60)
    print(f"  模型     : {model}")
    print(f"  API Key  : {masked}")
    if base_url:
        print(f"  Base URL : {base_url}（中转平台模式）")
    else:
        print(f"  Base URL : 官方直连")
    print("=" * 60)
    print()

    return api_key, base_url, model


def main():
    api_key, base_url, model = load_config()

    # 构造 LangChain ↔ Anthropic 客户端
    # 中转平台：追加 base_url 参数；官方直连：不传
    client_kwargs = {
        "model": model,
        "api_key": api_key,
        "max_tokens": 1024,
        "temperature": 0.7,
    }
    if base_url:
        # langchain-anthropic 支持 base_url 透传给 anthropic SDK
        client_kwargs["base_url"] = base_url

    llm = ChatAnthropic(**client_kwargs)

    print("正在请求 Claude API...")
    print("-" * 60)
    try:
        res = llm.invoke("简单介绍竞品情报分析的作用（150字以内）")
    except Exception as e:
        print("[ERROR] 请求失败")
        print("-" * 60)
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {e}")
        print("-" * 60)
        print("排查建议：")
        print("  1) 确认 API Key 正确且未过期")
        print("  2) 确认账户余额充足（https://console.anthropic.com/）")
        print("  3) 如使用中转平台，确认 ANTHROPIC_BASE_URL 地址可达")
        print("  4) 检查网络代理 / 防火墙是否放行")
        sys.exit(2)

    print("[OK] Claude 响应成功！")
    print("-" * 60)
    print(res.content)
    print("-" * 60)
    print(f"Token 用量: {res.response_metadata.get('usage', 'N/A')}")
    print()
    print("环境 / 密钥 / 网络 / LangChain 集成 全部正常 [OK]")


if __name__ == "__main__":
    main()
