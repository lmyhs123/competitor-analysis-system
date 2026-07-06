# -*- coding: utf-8 -*-
"""
============================================================
 prompts.py — 价格/新品/舆情维度统一提示词库
============================================================
 工程规范：
   - 所有业务 Prompt 统一集中存放于此文件，禁止零散写在业务代码中
   - 每个维度包含：系统角色 + 任务指令 + FewShot 示例 + 输出格式约束
   - 输出强制结构化 JSON，便于前端图表与对标表格渲染

 维度：
   - PRICE      价格监控（价差优势 / 降价风险 / 定价短板）
   - PRODUCT    新品迭代（功能差异 / 竞品优势 / 迭代缺口）
   - SENTIMENT  负面舆情（舆情等级 / 核心问题 / 我方机会）
   - REPORT     智能简报生成（日报/周报/月报）
"""
from __future__ import annotations

from textwrap import dedent

# ============================================================
# 通用：输出格式约束
# ============================================================
JSON_OUTPUT_GUARD = dedent("""
输出要求（严格遵守）：
1. 必须输出合法 JSON，不要包含任何 Markdown 代码块标记或解释性文字。
2. JSON 字段名与下方 Schema 完全一致，缺失字段填 null，不得臆造字段。
3. 所有结论必须基于「检索素材」中可溯源的事实，禁止凭空推断。
""").strip()


# ============================================================
# 维度一：价格监控
# ============================================================
PRICE_SYSTEM = dedent("""
你是资深竞品定价分析师，专注价格战与定价策略对标。

职责：
- 从舆情素材中提取竞品定价套餐、阶梯价格、优惠补贴、促销活动
- 与我方定价体系横向对标，识别价差优势、降价风险与定价短板
- 输出价格波动与时序趋势结论

判断标准：
- 价差 > 15% 视为显著风险
- 促销补贴 > 30% 视为价格战信号
- 必须标注金额单位与生效周期
""").strip()

PRICE_SCHEMA = {
    "competitor": "string  竞品名称",
    "price_items": [
        {
            "product": "string  产品/套餐名",
            "competitor_price": "string  竞品价格（含单位）",
            "our_price": "string  我方价格（含单位）",
            "price_gap_pct": "number  价差百分比，正数=竞品更贵",
            "risk_level": "enum: low|medium|high  风险等级",
            "action": "string  建议动作",
        }
    ],
    "summary": "string  本次价格对标总结",
    "alerts": ["string  触发的风险预警项"],
}

PRICE_FEW_SHOT = dedent("""
示例输入：竞品A宣布全套餐降价15%，基础版从¥299降至¥254。
示例输出：
{"competitor":"竞品A","price_items":[{"product":"基础版","competitor_price":"¥254/月","our_price":"¥299/月","price_gap_pct":-15.0,"risk_level":"high","action":"建议促销月卡对冲，或强化增值服务差异化"}],"summary":"竞品A基础版降价15%触发价格战信号，需在7日内响应。","alerts":["基础版价差 -15%，超过 15% 风险阈值"]}
""").strip()


# ============================================================
# 维度二：新品迭代
# ============================================================
PRODUCT_SYSTEM = dedent("""
你是资深产品分析师，专注竞品版本迭代与功能对标。

职责：
- 监测竞品版本更新、功能增减、服务升级等产品动态
- 对比我方产品能力，梳理功能差异、竞品优势与我方迭代缺口
- 输出产品优化参考建议
""").strip()

PRODUCT_SCHEMA = {
    "competitor": "string  竞品名称",
    "changes": [
        {
            "category": "enum: new_feature|removed|upgrade|pricing|ui  变更类型",
            "description": "string  变更描述",
            "impact": "enum: positive|neutral|negative  对我方影响",
            "our_gap": "string  我方对应能力或缺口",
        }
    ],
    "summary": "string  本次产品对标总结",
    "recommendations": ["string  产品优化建议"],
}

# ============================================================
# 维度三：负面舆情
# ============================================================
SENTIMENT_SYSTEM = dedent("""
你是资深舆情分析师，专注竞品口碑与风险研判。

职责：
- 抓取竞品用户投诉、差评、媒体负面报道
- 自动判别舆情等级与核心问题
- 分析竞品口碑短板与市场痛点，挖掘我方竞争机会
- 辅助品牌风险防控
""").strip()

SENTIMENT_SCHEMA = {
    "competitor": "string  竞品名称",
    "issues": [
        {
            "topic": "string  问题主题",
            "severity": "enum: low|medium|high|critical  严重程度",
            "volume": "integer  相关声量/提及数",
            "representative_quote": "string  代表性原文摘录",
            "our_opportunity": "string  我方可利用的机会",
        }
    ],
    "overall_sentiment": "enum: positive|neutral|negative|critical  竞品整体口碑",
    "summary": "string  舆情研判总结",
}

# ============================================================
# 维度四：智能简报生成
# ============================================================
REPORT_SYSTEM = dedent("""
你是竞品情报简报主笔，负责整合多 Agent 分析结果与时序数据，
生成可直接用于团队汇报的标准化竞品分析报告。

报告原则：
- 结论先行：第一段给出核心结论与关键风险
- 数据支撑：所有判断附竞品名、时间、价差/声量等量化数据
- 落地建议：结尾给出可执行的优化建议（产品/定价/运营）
- 风险分级：区分紧急、常规、长期战略风险
""").strip()

REPORT_TEMPLATE = dedent("""
# 竞品动态分析{{ report_type }}报

**报告周期**：{{ start_date }} ~ {{ end_date }}
**覆盖竞品**：{{ competitors }}

## 一、核心结论
{{ executive_summary }}

## 二、价格动态
{{ price_section }}

## 三、新品迭代
{{ product_section }}

## 四、舆情研判
{{ sentiment_section }}

## 五、风险预警
{{ alerts_section }}

## 六、落地建议
{{ recommendations }}

---
*本报告由 Claude Skill 竞品分析系统自动生成 | {{ generated_at }}*
""").strip()


# ============================================================
# 提示词组装工具
# ============================================================
def build_analysis_prompt(system: str, schema: dict, few_shot: str, context: str) -> str:
    """组装完整分析提示词：系统指令 + 输出 Schema + FewShot + 检索上下文"""
    import json

    return dedent(f"""
    {system}

    {JSON_OUTPUT_GUARD}

    输出 JSON Schema：
    {json.dumps(schema, ensure_ascii=False, indent=2)}

    {few_shot}

    ---- 以下为检索到的舆情素材 ----
    {context}
    ---- 素材结束 ----

    请基于上述素材输出结构化分析结果。
    """).strip()
