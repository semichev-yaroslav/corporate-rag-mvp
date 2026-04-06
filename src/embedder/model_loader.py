from __future__ import annotations

class EmbeddingModelLoader:
    def __init__(self, settings) -> None:
        self.settings = settings
        self.model = None
        self.tokenizer = None
        self.device = settings.embedding_device
        self.max_length = 2048

    def load(self) -> None:
        if self.model is not None and self.tokenizer is not None:
            return

        try:
            import torch
            from transformers import AutoModel, AutoTokenizer, BitsAndBytesConfig
        except ImportError as error:
            raise RuntimeError(
                "Для embedder-сервиса нужны пакеты из extras `embedder`."
            ) from error

        if self.device == "cuda" and not torch.cuda.is_available():
            if not self.settings.embedder_allow_cpu_fallback:
                raise RuntimeError("CUDA недоступна, а CPU fallback отключен.")
            self.device = "cpu"

        kwargs = {"trust_remote_code": True}
        use_4bit = self.device == "cuda" and self.settings.embedding_quantization.lower() == "4bit"
        if use_4bit:
            kwargs["device_map"] = "auto"
            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
            )
        elif self.device == "cuda":
            kwargs["torch_dtype"] = torch.float16

        self.tokenizer = AutoTokenizer.from_pretrained(self.settings.embedding_model_id, trust_remote_code=True)
        self.model = AutoModel.from_pretrained(self.settings.embedding_model_id, **kwargs)
        self.model.eval()
        if not use_4bit:
            self.model.to(self.device)
        self.max_length = self._resolve_max_length()

    def embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        self.load()

        import torch
        import torch.nn.functional as F

        prepared = [self._format_text(text, task_type) for text in texts]
        vectors: list[list[float]] = []
        batch_size = 4

        for offset in range(0, len(prepared), batch_size):
            batch_texts = prepared[offset : offset + batch_size]
            encoded = self.tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt",
            )
            encoded = {
                key: value.to(self.device) if hasattr(value, "to") else value
                for key, value in encoded.items()
            }

            with torch.inference_mode():
                outputs = self.model(**encoded)

            if isinstance(outputs, dict) and "embeddings" in outputs:
                batch_vectors = outputs["embeddings"]
            elif hasattr(outputs, "last_hidden_state"):
                hidden = outputs.last_hidden_state
                attention = encoded["attention_mask"].unsqueeze(-1).expand(hidden.size()).float()
                summed = (hidden * attention).sum(dim=1)
                counts = attention.sum(dim=1).clamp(min=1e-9)
                batch_vectors = summed / counts
            else:
                raise RuntimeError("Не удалось получить эмбеддинги из модели.")

            batch_vectors = F.normalize(batch_vectors, p=2, dim=1)
            vectors.extend(batch_vectors.detach().cpu().tolist())

        return vectors

    def _format_text(self, text: str, task_type: str) -> str:
        clean = " ".join(text.split())
        if "e5" in self.settings.embedding_model_id.lower():
            prefix = "query" if task_type == "query" else "passage"
            return f"{prefix}: {clean}"
        if task_type == "query":
            return (
                "Instruct: Найди релевантные корпоративные документы и фрагменты.\n"
                f"Query: {clean}"
            )
        return f"Passage: {clean}"

    def _resolve_max_length(self) -> int:
        candidates: list[int] = []
        for value in (
            getattr(self.tokenizer, "model_max_length", None),
            getattr(getattr(self.model, "config", None), "max_position_embeddings", None),
            2048,
        ):
            if isinstance(value, int) and 0 < value <= 16384:
                candidates.append(value)
        return min(candidates) if candidates else 2048

_model_loader: EmbeddingModelLoader | None = None


def get_model_loader(settings):
    global _model_loader
    if _model_loader is None:
        _model_loader = EmbeddingModelLoader(settings)
    return _model_loader
