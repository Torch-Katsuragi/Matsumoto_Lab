"""
Imagen クライアント（Gemini API / generate_content ベース）

gemini-3-pro-image-preview を使用し、マルチモーダル入力で画像生成を行う。
参照画像は最大14枚まで入力可能。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List

import logging
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from .conf import IMAGEN3_MODEL
except ImportError:
    from image.conf import IMAGEN3_MODEL

try:
    from .conf import GOOGLE_API_KEY  # type: ignore
except Exception:
    try:
        from image.conf import GOOGLE_API_KEY  # type: ignore
    except Exception:
        GOOGLE_API_KEY = None  # type: ignore


# デフォルトモデル（gemini-3-pro-image-preview を推奨）
DEFAULT_MODEL = "gemini-3-pro-image-preview"


@dataclass(frozen=True)
class ImagenRequest:
    """CSV 1行に対応する生成リクエスト。"""

    prompt: str
    # 参照画像のリスト（最大14枚）
    ref_images: tuple[Path, ...] = field(default_factory=tuple)

    number_of_images: int = 1
    aspect_ratio: str = "1:1"  # 1:1, 16:9, 9:16, 4:3, 3:4
    resolution: str = "1K"  # 出力解像度: 1K, 2K, 4K
    seed: int | None = None


# 後方互換性
Imagen3Request = ImagenRequest


class ImagenClient:
    """
    Gemini API の generate_content を使った画像生成クライアント。
    """

    def __init__(
        self,
        project_id: str | None = None,
        location: str | None = None,
        model_name: str | None = None,
    ) -> None:
        # project_id, location は Gemini API では不要だが互換性のため残す
        self.model_name = model_name or IMAGEN3_MODEL or DEFAULT_MODEL

        # gemini-3-pro-image-preview に寄せる
        if self.model_name.startswith("imagen-"):
            self.model_name = DEFAULT_MODEL

        if not GOOGLE_API_KEY:
            raise ModuleNotFoundError(
                "GOOGLE_API_KEY is not set. Set it in .env for Gemini API."
            )

        self._client = _init_genai_client(GOOGLE_API_KEY)

    def generate(self, req: ImagenRequest) -> List[bytes]:
        """
        プロンプトと参照画像から画像を生成する。

        プロンプト内で {0}, {1}, ... を使って参照画像の挿入位置を指定可能。
        例: "{0}のキャラクターを{1}のスタイルで描いてください"
        → [img[0], "のキャラクターを", img[1], "のスタイルで描いてください"]
        """
        logging.info("Gemini Image Generation start (model=%s, refs=%d)", self.model_name, len(req.ref_images))

        try:
            from google.genai import types  # type: ignore
            from PIL import Image  # type: ignore
        except ImportError as e:
            raise ModuleNotFoundError(f"Required package not found: {e}")

        # 参照画像を読み込む
        images = [Image.open(ref_path) for ref_path in req.ref_images]

        # プロンプトをパースしてマルチモーダル入力を構築
        contents = _parse_prompt_with_placeholders(req.prompt, images)

        # 画像設定を構築
        image_config = types.ImageConfig(
            aspect_ratio=req.aspect_ratio,
            image_size=req.resolution,
        )

        # 生成リクエスト
        response = self._client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
                image_config=image_config,
            )
        )

        # 結果から画像を抽出
        return _extract_images_from_response(response)


# 後方互換性
Imagen3Client = ImagenClient


import re


def _parse_prompt_with_placeholders(prompt: str, images: List[Any]) -> List[Any]:
    """
    プロンプト内の {0}, {1}, ... を対応する画像に置き換えてマルチモーダル入力を構築する。

    例:
      prompt = "{0}のキャラクターを{1}のスタイルで描いてください"
      images = [img0, img1]
      → [img0, "のキャラクターを", img1, "のスタイルで描いてください"]

    プレースホルダーがない場合は、画像を先に並べてからプロンプトを追加する。
    """
    # プレースホルダー {数字} を探す
    pattern = re.compile(r"\{(\d+)\}")
    matches = list(pattern.finditer(prompt))

    if not matches:
        # プレースホルダーがない場合は従来通り：画像 → プロンプト
        return list(images) + [prompt] if images else [prompt]

    contents: List[Any] = []
    last_end = 0

    for match in matches:
        # プレースホルダーの前のテキストを追加
        if match.start() > last_end:
            text = prompt[last_end:match.start()]
            if text:
                contents.append(text)

        # 対応する画像を追加
        idx = int(match.group(1))
        if 0 <= idx < len(images):
            contents.append(images[idx])
        else:
            # 範囲外の場合はプレースホルダーをそのまま残す
            contents.append(match.group(0))

        last_end = match.end()

    # 残りのテキストを追加
    if last_end < len(prompt):
        text = prompt[last_end:]
        if text:
            contents.append(text)

    return contents


def _init_genai_client(api_key: str):
    try:
        from google import genai  # type: ignore

        if hasattr(genai, "Client"):
            return genai.Client(api_key=api_key)
        raise RuntimeError("google.genai.Client not found")
    except Exception as e:
        raise ModuleNotFoundError(
            "google-genai is required.\n"
            f"Install: {sys.executable} -m pip install google-genai"
        ) from e


def _extract_images_from_response(response: Any) -> List[bytes]:
    """
    generate_content のレスポンスから画像バイトを抽出する。
    """
    images: List[bytes] = []

    if not response.candidates:
        raise ValueError("No candidates in response")

    for candidate in response.candidates:
        if not candidate.content:
            continue
        for part in candidate.content.parts:
            if part.inline_data and part.inline_data.data:
                images.append(bytes(part.inline_data.data))

    if not images:
        # テキストのみの応答の場合
        text_parts = []
        for candidate in response.candidates:
            if candidate.content:
                for part in candidate.content.parts:
                    if part.text:
                        text_parts.append(part.text)
        if text_parts:
            raise ValueError(f"No image in response. Text: {' '.join(text_parts)}")
        raise ValueError("No image in response")

    return images
