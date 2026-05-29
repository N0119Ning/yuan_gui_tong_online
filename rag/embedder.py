"""BGE-small embedding manager — lightweight (91MB) Chinese-optimized model."""

import os
from pathlib import Path
from chromadb.api.types import EmbeddingFunction
from sentence_transformers import SentenceTransformer

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

_SMALL_MODEL = Path(__file__).parent.parent / "models" / "BAAI" / "bge-small-zh-v1___5"
_BGE_M3 = Path(__file__).parent.parent / "models" / "BAAI" / "bge-m3"

# Default to small model, fall back to M3 if small not found
_DEFAULT_MODEL = str(_SMALL_MODEL) if _SMALL_MODEL.exists() else (
    str(_BGE_M3) if _BGE_M3.exists() else "BAAI/bge-small-zh-v1.5"
)


class BgeSmallEmbeddingFunction(EmbeddingFunction):
    def __init__(self, model_path: str = None):
        self._model_path = model_path or _DEFAULT_MODEL
        self._model = None

    @property
    def _lazy_model(self):
        if self._model is None:
            self._model = SentenceTransformer(self._model_path)
        return self._model

    def __call__(self, input):
        return self._lazy_model.encode(
            list(input), batch_size=32, show_progress_bar=False
        ).tolist()


class EmbeddingManager:
    def __init__(self, model_path: str = None):
        self.model_path = model_path or _DEFAULT_MODEL
        self.provider = "bge-small-zh-v1.5"
        self.embedding_function = BgeSmallEmbeddingFunction(self.model_path)

    def embed_query(self, text: str):
        return self.embedding_function([text])[0]

    def embed_documents(self, texts: list):
        return self.embedding_function(texts)

    def get_dimension(self) -> int:
        return 512
