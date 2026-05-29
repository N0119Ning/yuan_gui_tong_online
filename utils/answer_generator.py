"""Answer generation with precise standard citations."""

from .llm_client import LLMClient

SYSTEM_PROMPT = """你是一个风景园林设计规范智能助手（园规通）。你的任务是：
1. 根据用户问题，从检索到的规范条款中找到最相关的内容
2. 生成准确、简洁的回答
3. 每个回答必须包含精确的引用来源：规范名称 + 条款号 + 原文摘录

规则：
- 只使用提供的规范条款，不要编造或猜测
- 如果检索结果中没有相关内容，诚实地告诉用户"未找到相关规范条款"
- 回答格式：先给出结论，再列出引用来源
- 引用格式：[规范名称] 第X.X条："原文摘录"
- 数值范围用"至"或"～"（全角），禁止用半角"~"（会被Markdown解析为删除线）
"""


class AnswerGenerator:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def generate(self, query: str, results: list) -> str:
        if not results:
            return "未找到相关规范条款。请尝试更换关键词或确认知识库中已包含相关规范。"

        context_parts = []
        for i, r in enumerate(results, 1):
            meta = r.get("metadata", {})
            code = meta.get("standard_code", "未知规范")
            name = meta.get("standard_name", "")
            clause = meta.get("clause_number", "相关条款")
            content = r.get("content", "")

            context_parts.append(
                f"[{i}] {code} {name} 第{clause}条:\n{content}"
            )

        context = "\n\n".join(context_parts)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"【检索到的规范条款】\n\n{context}\n\n【用户问题】\n{query}\n\n请根据以上规范条款回答用户问题，并给出精确引用来源。"},
        ]

        return self.llm.chat(messages)
