# 园规通 — 风景园林设计规范智能助手

自然语言查询，精确条款引用。覆盖 **9 本**风景园林核心国标/行标，**1168 条**条款。

---

## 功能特性

- **自然语言检索**：输入问题即可检索相关规范条款，支持数值查询、事实查询、跨标准对比、术语定义
- **精确引用**：LLM 生成回答时自动附上规范名称 + 条款号 + 原文摘录
- **扫描件 OCR**：PaddleOCR 自动识别图像 PDF，识别结果缓存复用
- **增量构建**：新增 PDF 自动追加到向量库，不影响已有数据
- **邀请码系统**：每人每天 20 次提问，支持赞踩反馈收集
- **对话日志**：SQLite 持久化所有问答记录，按邀请码统计使用情况

---

## 技术架构

```
用户提问 → Streamlit 界面
              ↓
       混合检索（向量 50% + jieba 关键词 50%）
              ↑
       ChromaDB 向量库（1168 条，持久化）
              ↑
       条款切分（正则匹配 + 噪声过滤）
              ↑
       PDF 解析（PyMuPDF 文本层 + PaddleOCR 扫描件兜底）
              ↓
       DeepSeek-chat → 精确引用回答
```

---

## 构建流程

### 首次构建（本地）

```bash
# 1. 安装依赖
pip install streamlit chromadb sentence-transformers jieba openai python-dotenv
pip install paddleocr paddlepaddle pymupdf opencv-python

# 2. 将规范 PDF 放入 data/standards/
# 命名格式：GB50180-2018_城市居住区规划设计标准.pdf

# 3. 初始化知识库
python build_kb.py
# 或直接在 Streamlit 界面点击「初始化」

# 4. 设置 API Key
echo "DEEPSEEK_API_KEY=sk-xxx" > .env

# 5. 启动
streamlit run app.py --server.port 8503
```

### 增量添加新规范

```bash
# 将新 PDF 放入 data/standards/ 后，启动应用点击「初始化」即可
# 系统自动检测已有标准，只处理新增的 PDF
# OCR 结果缓存到 data/ocr_cache/，后续构建秒级读取
```

### 构建耗时

| 阶段 | 首次 | 增量 | 使用缓存 |
|------|------|------|----------|
| PDF 解析 | ~15 min（266 页扫描件） | 仅新 PDF | 秒级 |
| 条款切分 | ~5 s | ~5 s | ~5 s |
| 向量嵌入 | ~15 min（CPU） | 仅新条款 | 仅新条款 |

> **首次构建总计约 30 分钟。后续启动直接加载 ChromaDB，2 秒就绪。**

---

## 嵌入模型对比：BGE-M3 vs bge-small-zh-v1.5

我们对两种嵌入模型进行了 A/B 测试（60 题评测集、相同数据）：

| 指标 | BGE-M3 (4.3GB/1024d) | bge-small (91MB/512d) | 差异 |
|------|----------------------|----------------------|------|
| **Recall@5** | 89.4% | **91.1%** | +1.7% |
| **Precision@5** | 53.6% | **57.3%** | +3.7% |
| **MRR** | 82.9% | **77.8%** | -5.1% |
| **NDCG@5** | 82.7% | **79.1%** | -3.6% |
| **零召回** | 0/60 | 0/60 | = |
| **模型大小** | 4.3 GB | 91 MB | **47× 缩小** |
| **加载时间** | ~30 s | ~2 s | **15× 加速** |

> **结论：bge-small-zh-v1.5 检索质量与 BGE-M3 基本持平（召回率和查准率甚至略高），体积缩小 47 倍。**
>
> 项目已切换至 bge-small-zh-v1.5 作为默认嵌入模型。

---

## 评测指标

### 60 题评测结果

| 指标 | 分值 | 说明 |
|------|------|------|
| **Recall@5** | 91.1% | Top-5 去重后命中的相关规范比例 |
| **Precision@5** | 57.3% | Top-5 去重结果中真正相关的比例 |
| **MRR** | 0.778 | 第一个正确答案的平均排位倒数 |
| **NDCG@5** | 0.791 | 考虑相关度分级的排序质量 |
| **零召回题** | 0 | 没有完全找不到的情况 |

### 评测覆盖

| 标准 | 题目数 | 类型 |
|------|--------|------|
| GB50016（建筑设计防火规范） | 6 | 数值/事实/条件查询 |
| GB50180（城市居住区规划设计标准） | 6 | 数值/事实查询 |
| GB50420（城市绿地设计规范） | 6 | 数值/跨标准对比 |
| GB51192（公园设计规范） | 7 | 数值/事实/概述查询 |
| GB50763（无障碍设计规范） | 5 | 数值/事实查询 |
| CJJ82（园林绿化施工验收规范） | 5 | 数值/事实查询 |
| CJJ37（城市道路绿化设计标准） | 5 | 数值/事实查询 |
| GB55014（园林绿化工程项目规范） | 3 | 事实/强制条文 |
| CJJT91（风景园林基本术语标准） | 5 | 术语/定义查询 |
| 跨标准对比 | 6 | 不同规范间关联查询 |
| 无结果边界 | 1 | 预期无结果的边界测试 |

---

## 项目结构

```
yuan_gui_tong/
├── app.py                  # Streamlit 主界面（欢迎页、邀请码、问答）
├── build_kb.py             # 知识库构建脚本
├── eval_retrieval.py       # 评测脚本（一键生成 Recall/Precision/MRR/NDCG）
├── requirements_online.txt # 线上部署精简依赖
├── rag/
│   ├── embedder.py         # bge-small-zh-v1.5 嵌入（91MB）
│   ├── retriever.py        # 混合检索（语义 + jieba 关键词）
│   ├── clause_chunker.py   # 条款切分 + 噪声过滤
│   ├── pdf_parser.py       # PDF 解析（文本层 + OCR 兜底 + 结果缓存）
│   └── knowledge_base.py   # 编排全流程（增量构建）
├── utils/
│   ├── llm_client.py       # DeepSeek API 封装（3次重试）
│   ├── answer_generator.py # 回答生成（引用格式 prompt）
│   ├── conversation_logger.py # SQLite 对话日志
│   └── badcase_logger.py   # JSONL badcase 记录
├── data/
│   ├── chroma_db/          # 向量库（SQLite 持久化，重启不丢）
│   ├── standards/          # 9 本规范 PDF（~41MB）
│   ├── ocr_cache/          # OCR 结果缓存 txt
│   ├── eval_questions.json # 60 题评测集
│   ├── eval_results.json   # 评测结果
│   └── invite_codes.json   # 邀请码配置
└── models/BAAI/bge-small-zh-v1___5/  # 嵌入模型（91MB）
```

---

## 线上部署

在线版预构建知识库，打开即用，无需初始化。

**部署地址：** `https://huggingface.co/spaces/E1owen/yuan_gui_tong`

线上版精简依赖（不含 PaddleOCR/PyMuPDF）：
```bash
pip install -r requirements_online.txt  # 仅 7 个包
streamlit run app.py
```

详见独立部署仓库：[yuan_gui_tong_online](https://github.com/N0119Ning/yuan_gui_tong_online)

---

## 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 前端 | Streamlit | 单文件 app.py |
| 向量库 | ChromaDB | SQLite 持久化 |
| 嵌入模型 | bge-small-zh-v1.5 | 91MB, 512 维, CPU |
| 分词 | jieba | 中文关键词提取 |
| OCR | PaddleOCR | 扫描件兜底 |
| PDF 解析 | PyMuPDF | 文本层主力 |
| LLM | DeepSeek-chat | API 调用 |
| 日志 | SQLite | 对话记录 + 统计 |
