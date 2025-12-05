from __future__ import annotations

import asyncio
from functools import partial
from typing import Optional, List

from FlagEmbedding import FlagModel
import torch

DEFAULT_MODEL_NAME = "BAAI/bge-m3"
QUERY_INSTRUCTION = "Represent this question for retrieving the same or highly similar exam questions:"


class EmbeddingService:
    """BGE-M3 embedding 服务，单例模式，支持异步调用"""

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME, device: Optional[str] = None):
        self.model_name = model_name
        self.device = device
        self._model: Optional[FlagModel] = None
        self._lock = asyncio.Lock()

    def _resolve_device(self) -> str:
        if self.device:
            return self.device
        return "cuda" if torch.cuda.is_available() else "cpu"

    async def _load_model(self) -> FlagModel:
        if self._model is not None:
            return self._model
        async with self._lock:
            if self._model is None:
                device = self._resolve_device()
                loop = asyncio.get_running_loop()
                self._model = await loop.run_in_executor(
                    None,
                    lambda: FlagModel(
                        self.model_name,
                        query_instruction_for_retrieval=QUERY_INSTRUCTION,
                        use_fp16=(device == "cuda"),
                        device=device,
                    )
                )
        return self._model

    async def embed_query(self, text: str) -> List[float]:
        """生成查询文本的 embedding 向量（用于检索时的查询端）"""
        model = await self._load_model()
        loop = asyncio.get_running_loop()
        encode_fn = partial(
            model.encode_queries,
            [text],
            batch_size=1,
            normalize_embeddings=True,
        )
        vectors = await loop.run_in_executor(None, encode_fn)
        return vectors[0].tolist()

    async def embed_passage(self, text: str) -> List[float]:
        """生成文档文本的 embedding 向量（用于存储到数据库的文档端）"""
        model = await self._load_model()
        loop = asyncio.get_running_loop()
        encode_fn = partial(
            model.encode_corpus,
            [text],
            batch_size=1,
            normalize_embeddings=True,
        )
        vectors = await loop.run_in_executor(None, encode_fn)
        return vectors[0].tolist()

    async def embed_passages_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """批量生成文档 embedding 向量"""
        if not texts:
            return []
        model = await self._load_model()
        loop = asyncio.get_running_loop()
        encode_fn = partial(
            model.encode_corpus,
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
        )
        vectors = await loop.run_in_executor(None, encode_fn)
        return [v.tolist() for v in vectors]


_SERVICE: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """获取全局 EmbeddingService 单例"""
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = EmbeddingService()
    return _SERVICE
