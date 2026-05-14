"""Image embeddings via OpenCLIP (open weights, runs locally).

ViT-B-32 produces 512-dim; we use ViT-L-14 for 768-dim to match the schema.
First load downloads ~890 MB.
"""
from __future__ import annotations

import io
from functools import lru_cache

from adspy.utils.logging import get_logger

log = get_logger(__name__)

MODEL_NAME = "ViT-L-14"
PRETRAINED = "openai"
DIM = 768


@lru_cache(maxsize=1)
def _model_and_preprocess():  # type: ignore[no-untyped-def]
    import open_clip

    log.info("image_embedding_model_loading", model=MODEL_NAME)
    model, _, preprocess = open_clip.create_model_and_transforms(
        MODEL_NAME, pretrained=PRETRAINED
    )
    model.eval()
    return model, preprocess


def embed_image_bytes(data: bytes) -> list[float] | None:
    try:
        import torch
        from PIL import Image
    except ImportError:
        return None
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        return None
    model, preprocess = _model_and_preprocess()
    with torch.no_grad():
        tensor = preprocess(img).unsqueeze(0)
        feats = model.encode_image(tensor)
        feats = feats / feats.norm(dim=-1, keepdim=True)
    return [float(x) for x in feats[0].tolist()]
