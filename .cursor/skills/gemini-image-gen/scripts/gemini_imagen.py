"""
Gemini API 画像生成クライアント（自己完結型）

google-genai の generate_content を使い、テキストや参照画像から画像を生成する。
参照画像は最大14枚まで入力可能。プロンプト内で {0}, {1}, ... を使って挿入位置を指定できる。

必要パッケージ: google-genai, Pillow, python-dotenv(任意)
環境変数: GOOGLE_API_KEY（必須）, IMAGEN_MODEL（任意）
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List

# .env の読み込み（python-dotenv がなくても動作する）
try:
    from dotenv import load_dotenv

    load_dotenv()
except ModuleNotFoundError:
    pass

GOOGLE_API_KEY: str | None = os.environ.get("GOOGLE_API_KEY")
DEFAULT_MODEL: str = os.environ.get("IMAGEN_MODEL") or "gemini-2.0-flash-preview-image-generation"


@dataclass(frozen=True)
class ImagenRequest:
    """画像生成リクエスト。"""

    prompt: str
    ref_images: tuple[Path, ...] = field(default_factory=tuple)
    number_of_images: int = 1
    aspect_ratio: str = "1:1"
    resolution: str = "1K"
    seed: int | None = None


class ImagenClient:
    """Gemini API の generate_content を使った画像生成クライアント。"""

    def __init__(self, *, model_name: str | None = None, api_key: str | None = None) -> None:
        self.model_name = model_name or DEFAULT_MODEL
        key = api_key or GOOGLE_API_KEY
        if not key:
            raise RuntimeError(
                "GOOGLE_API_KEY が未設定。.env または環境変数で設定してください。"
            )
        self._client = _init_genai_client(key)

    def generate(self, req: ImagenRequest) -> List[bytes]:
        """プロンプトと参照画像から画像を生成し、バイト列のリストを返す。"""
        logging.info("Gemini 画像生成開始 (model=%s, refs=%d)", self.model_name, len(req.ref_images))

        try:
            from google.genai import types  # type: ignore
            from PIL import Image  # type: ignore
        except ImportError as e:
            raise ModuleNotFoundError(f"必要なパッケージが見つかりません: {e}")

        images = [Image.open(p) for p in req.ref_images]
        contents = _parse_prompt_with_placeholders(req.prompt, images)

        response = self._client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
                image_config=types.ImageConfig(
                    aspect_ratio=req.aspect_ratio,
                    image_size=req.resolution,
                ),
            ),
        )
        return _extract_images_from_response(response)


# ---------------------------------------------------------------------------
# 内部ヘルパー
# ---------------------------------------------------------------------------

_PLACEHOLDER_RE = re.compile(r"\{(\d+)\}")


def _parse_prompt_with_placeholders(prompt: str, images: List[Any]) -> List[Any]:
    """
    プロンプト内の {0}, {1}, ... を対応する画像に置き換えてマルチモーダル入力を構築する。
    プレースホルダーがない場合は画像を先に並べてからプロンプトを追加する。
    """
    matches = list(_PLACEHOLDER_RE.finditer(prompt))
    if not matches:
        return list(images) + [prompt] if images else [prompt]

    contents: List[Any] = []
    last_end = 0
    for m in matches:
        text = prompt[last_end : m.start()]
        if text:
            contents.append(text)
        idx = int(m.group(1))
        contents.append(images[idx] if 0 <= idx < len(images) else m.group(0))
        last_end = m.end()

    tail = prompt[last_end:]
    if tail:
        contents.append(tail)
    return contents


def _init_genai_client(api_key: str):
    try:
        from google import genai  # type: ignore

        if hasattr(genai, "Client"):
            return genai.Client(api_key=api_key)
        raise RuntimeError("google.genai.Client が見つかりません")
    except Exception as e:
        raise ModuleNotFoundError(
            "google-genai が必要です。\n"
            f"インストール: {sys.executable} -m pip install google-genai"
        ) from e


def _extract_images_from_response(response: Any) -> List[bytes]:
    """generate_content のレスポンスから画像バイトを抽出する。"""
    if not response.candidates:
        raise ValueError("レスポンスに候補がありません")

    images: List[bytes] = []
    for candidate in response.candidates:
        if not candidate.content:
            continue
        for part in candidate.content.parts:
            if part.inline_data and part.inline_data.data:
                images.append(bytes(part.inline_data.data))

    if images:
        return images

    # 画像なし — テキスト応答があればエラーに含める
    texts = []
    for candidate in response.candidates:
        if candidate.content:
            for part in candidate.content.parts:
                if part.text:
                    texts.append(part.text)
    detail = f" Text: {' '.join(texts)}" if texts else ""
    raise ValueError(f"レスポンスに画像が含まれていません。{detail}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gemini_imagen",
        description="Gemini API で画像を生成する。",
    )
    p.add_argument("--prompt", required=True, help="生成プロンプト")
    p.add_argument("--ref-images", nargs="*", default=[], help="参照画像パス（複数指定可）")
    p.add_argument("--output", "-o", type=Path, default=Path("output.png"), help="出力ファイルパス")
    p.add_argument("--aspect-ratio", default="1:1", help="アスペクト比 (1:1, 16:9, 9:16, 4:3, 3:4)")
    p.add_argument("--resolution", default="1K", help="解像度 (1K, 2K, 4K)")
    p.add_argument("--number", type=int, default=1, help="生成枚数")
    p.add_argument("--model", default=None, help="モデル名")
    return p


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    args = _build_parser().parse_args()

    client = ImagenClient(model_name=args.model)
    req = ImagenRequest(
        prompt=args.prompt,
        ref_images=tuple(Path(p) for p in args.ref_images),
        number_of_images=args.number,
        aspect_ratio=args.aspect_ratio,
        resolution=args.resolution,
    )
    result = client.generate(req)

    out: Path = args.output
    out.parent.mkdir(parents=True, exist_ok=True)

    if len(result) == 1:
        out.write_bytes(result[0])
        logging.info("保存: %s", out)
    else:
        for i, b in enumerate(result, 1):
            p = out.with_name(f"{out.stem}_{i:02d}{out.suffix}")
            p.write_bytes(b)
            logging.info("保存: %s", p)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
