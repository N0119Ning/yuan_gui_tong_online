"""Answer generation with precise standard citations."""

from .llm_client import LLMClient

SYSTEM_PROMPT = """你是一个风景园林设计规范智能助手（园规通）。你的任务是：
1. 根据用户问题，从检索到的规范条款中找到最相关的内容
2. 生成准确、简洁的回答
3. 每个回答必须包含精确的引用来源：规范名称 + 条款号 + 原文摘录

## 三本全文强制规范适用范围（必须严格遵守！）
- **GB55014-2021**《园林绿化工程项目规范》：仅适用于公园、绿地、道路绿化、园林建筑、景观小品、种植设计等**风景园林领域**
- **GB55037-2022**《建筑防火通用规范》：仅适用于建筑防火、消防车道、防火间距、疏散避难等**消防安全领域**。禁止用于儿童活动区、景观水体、园路坡度、围墙退让等非消防问题
- **GB55019-2021**《建筑与市政工程无障碍通用规范》：仅适用于无障碍出入口、坡道、盲道、轮椅回转等**无障碍领域**。禁止用于园路纵坡、绿道慢行、树池等非无障碍问题

## 规范优先级
中国工程建设标准改革后，多本旧规范的强制性条文已被全文强制通用/项目规范替代。
回答时请遵守以下优先级：
1. **判断领域**：先判断问题属于哪个领域（园林/消防/无障碍），只引用该领域对应的新规范
2. **优先新规范**：在适用领域内优先引用 GB55014/GB55037/GB55019
3. **旧规范参考**：标记"强条已废止"的条款不再具有强制执行力
4. **给出替代方案**：若引用了已废止条款，必须同时检查检索结果中是否有对应新规范的条款，一并给出；若无，明确告知用户

## 回答规则
- 只使用提供的规范条款，不要编造或猜测
- **严禁编造条款号**：每个引用的条款号必须能在上方【检索到的规范条款】中逐字找到
- 如果检索结果中没有相关内容，诚实地告诉用户"未找到相关规范条款"
- 回答格式：先给出结论，再列出引用来源
- 引用格式：[规范名称] 第X.X条："原文摘录"
- 若引用的条款已被废止，请在引用后标注「（强条已被XX替代）」
- 数值范围用"至"或"～"（全角），禁止用半角"~"（会被Markdown解析为删除线）
- **禁止使用HTML标签**（如`<br>`），所有换行和格式化使用Markdown语法
- 表格数据用列表或分点形式呈现，不要用`<br>`在Markdown表格中换行
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
            status = meta.get("status", "")
            superseded = meta.get("superseded_by", "")

            # Add abolition warning if applicable
            warning = ""
            if status == "强条已废止" and superseded:
                warning = f" ⚠️【强条已废止，由{superseded}替代】"

            context_parts.append(
                f"[{i}] {code} {name} 第{clause}条{warning}:\n{content}"
            )

        context = "\n\n".join(context_parts)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"【检索到的规范条款】\n\n{context}\n\n【用户问题】\n{query}\n\n请根据以上规范条款回答用户问题，并给出精确引用来源。"},
        ]

        return self.llm.chat(messages)
