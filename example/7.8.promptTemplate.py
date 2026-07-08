from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

# 初始化 DeepSeek
llm = ChatOpenAI(
    model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
    openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1",
    temperature=0.0,
)

# 定义提示词模板
template = """
你是一个竞品情报分析师。请根据以下信息，生成一份简洁的竞品分析摘要。
产品名称：{product}
竞争对手：{competitor}
关键差异点：{key_points}
"""

prompt = PromptTemplate(
    input_variables=["product", "competitor", "key_points"],
    template=template
)

# 构建 LCEL 链路
chain = prompt | llm | StrOutputParser()

# 传入参数调用并输出结果
result = chain.invoke({
    "product": "DeepSeek大模型",
    "competitor": "其他开源大模型",
    "key_points": "推理速度更快、上下文窗口更大、API调用成本更低"
})

# 打印输出结果
print("=== 竞品分析摘要 ===")
print(result)
