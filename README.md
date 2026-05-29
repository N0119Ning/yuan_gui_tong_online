# 园规通 — 风景园林设计规范智能助手

自然语言查询，精确条款引用。覆盖 9 本风景园林核心国标/行标，1168 条条款。

## 本地运行

```bash
# 1. 安装依赖
pip install -r requirements_online.txt

# 2. 设置 API Key
echo "DEEPSEEK_API_KEY=sk-xxx" > .env

# 3. 启动
streamlit run app.py --server.port 8503
```

首次使用需先构建知识库（需要 PaddleOCR + PyMuPDF）：

```bash
pip install paddleocr paddlepaddle pymupdf opencv-python
# 将规范 PDF 放入 data/standards/
python build_kb.py
```

## HuggingFace Spaces 部署

[![Open in Spaces](https://huggingface.co/datasets/huggingface/badges/raw/main/open-in-hf-spaces-sm.svg)](https://huggingface.co/spaces)

线上版已预构建知识库，打开即用，无需初始化。

## 项目结构

```
├── app.py                 # Streamlit 主界面
├── eval_retrieval.py      # 评测脚本
├── rag/                   # RAG 核心
│   ├── embedder.py        # bge-small-zh-v1.5 嵌入
│   ├── retriever.py       # 混合检索
│   ├── clause_chunker.py  # 条款切分
│   ├── pdf_parser.py      # PDF 解析
│   └── knowledge_base.py  # 知识库编排
├── utils/                 # 工具
├── data/                  # 数据
│   ├── chroma_db/         # 向量库（持久化）
│   ├── standards/         # 规范 PDF
│   └── ocr_cache/         # OCR 缓存
└── models/                # 嵌入模型
```

## 技术栈

Streamlit · ChromaDB · bge-small-zh-v1.5 · jieba · PaddleOCR · DeepSeek-chat
