from pathlib import Path
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_classic.chains import LLMChain

# 读取项目根目录 .env
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    raise RuntimeError("请先在 .env 中配置 DEEPSEEK_API_KEY")

llm = ChatOpenAI(
    model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
    api_key=api_key,
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
    temperature=0.7,
)

template = """
你是一个竞品情报分析师。请根据以下信息，生成一份简洁的竞品分析摘要。

产品名称：{product}
竞争对手：{competitor}
关键差异点：{key_points}

要求：
1. 先概括产品定位
2. 再分析相对竞品的优势
3. 最后给出一句市场竞争建议
"""

prompt = PromptTemplate(
    input_variables=["product", "competitor", "key_points"],
    template=template,
)

chain = LLMChain(llm=llm, prompt=prompt)

result = chain.invoke({
    "product": "DeepSeek大模型",
    "competitor": "主流开源大模型",
    "key_points": "推理速度更快、上下文窗口更大、API调用成本更低"
})

print("=== LLMChain 竞品分析摘要 ===")
print(result["text"])