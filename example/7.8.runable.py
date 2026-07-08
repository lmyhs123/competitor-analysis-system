from dotenv import load_dotenv
import os
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
  
  # 加载环境变量
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")
  
  # 1. 初始化DeepSeek模型
llm = ChatOpenAI(
      model="deepseek-chat",
      api_key=os.getenv("DEEPSEEK_API_KEY"),
      base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
      temperature=0.4
  )
  
  # 2. 定义竞品分析Prompt模板
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
  
  # 3. 基础串行RunnableSequence（透传完整入参，直接输出结果）
sequence = (
      {"product": RunnablePassthrough(), "competitor": RunnablePassthrough(), "key_points": RunnablePassthrough()}
      | prompt
      | llm
      | StrOutputParser()
  )
  
  # 测试基础链路
print("===== 基础RunnableSequence输出 =====")
res1 = sequence.invoke({
      "product": "DeepSeek大模型",
      "competitor": "主流开源大模型",
      "key_points": "推理延迟低、长上下文支持、商用API价格低廉"
  })
print(res1)
  
  # 4. 自定义处理函数：截取文本前50字符作为精简关键词
def extract_keywords(text):
      return text[:50]
  
  # 带预处理逻辑的复合链路
sequence_with_parse = (
      RunnableLambda(lambda x: extract_keywords(x["raw_text"]))
      | (lambda short_text: {
          "product": "DeepSeek",
          "competitor": "竞品AI模型",
          "key_points": short_text
      })
      | prompt
      | llm
      | StrOutputParser()
  )
  
  # 测试带预处理的链路
print("\n===== 带RunnableLambda预处理链路输出 =====")
raw_info = "推理速度快、支持128K上下文、本地部署轻量化、企业商用授权友好、API计费性价比极高"
res2 = sequence_with_parse.invoke({"raw_text": raw_info})
print(res2)
