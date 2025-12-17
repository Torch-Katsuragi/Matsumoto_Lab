"""
顔検出を使った1:1クロップユーティリティ

Gemini APIを使用して顔の位置を検出し、顔を中心に正方形クロップを行う。
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path

from PIL import Image, ImageOps

# パスを追加
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    from image.conf import GOOGLE_API_KEY
except ImportError:
    from conf import GOOGLE_API_KEY

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# サポートする画像拡張子
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# Gemini クライアント（遅延初期化）
_genai_client = None


def get_genai_client():
    """Gemini APIクライアントを取得"""
    global _genai_client
    if _genai_client is None:
        from google import genai
        _genai_client = genai.Client(api_key=GOOGLE_API_KEY)
    return _genai_client


def detect_face_center_gemini(image: Image.Image) -> tuple[int, int] | None:
    """
    Gemini APIを使って顔の中心座標を検出
    
    Args:
        image: PIL画像
        
    Returns:
        (center_x, center_y) or None if no face detected
    """
    from google.genai import types
    
    client = get_genai_client()
    w, h = image.size
    
    # 顔検出用プロンプト
    prompt = f"""Analyze this image and find the main face (person's face).
Return ONLY a JSON object with the face bounding box coordinates.
The image size is {w}x{h} pixels.

If a face is found, return:
{{"found": true, "x": <left>, "y": <top>, "width": <width>, "height": <height>}}

If no face is found, return:
{{"found": false}}

Return ONLY the JSON, no other text."""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[image, prompt],
            config=types.GenerateContentConfig(
                response_modalities=["TEXT"],
            )
        )
        
        # レスポンスからJSONを抽出
        text = ""
        for candidate in response.candidates:
            if candidate.content:
                for part in candidate.content.parts:
                    if part.text:
                        text += part.text
        
        # JSONをパース
        json_match = re.search(r'\{[^}]+\}', text)
        if json_match:
            data = json.loads(json_match.group())
            if data.get("found"):
                x = data["x"]
                y = data["y"]
                width = data["width"]
                height = data["height"]
                center_x = x + width // 2
                center_y = y + height // 2
                return (center_x, center_y)
        
        return None
        
    except Exception as e:
        logger.warning(f"Face detection API error: {e}")
        return None


def crop_square_around_center(
    image: Image.Image,
    center: tuple[int, int]
) -> Image.Image:
    """
    指定した中心を基準に正方形クロップを行う
    正方形の一辺は画像の短辺と同一
    
    Args:
        image: PIL画像
        center: クロップ中心座標 (x, y)
        
    Returns:
        クロップされた正方形画像
    """
    w, h = image.size
    cx, cy = center
    
    # 正方形のサイズ = 画像の短辺（情報の欠落を最小限に）
    crop_size = min(w, h)
    half = crop_size // 2
    
    # 左上座標を計算（中心を基準に）
    x1 = cx - half
    y1 = cy - half
    
    # 境界チェックと調整
    if x1 < 0:
        x1 = 0
    if y1 < 0:
        y1 = 0
    if x1 + crop_size > w:
        x1 = w - crop_size
    if y1 + crop_size > h:
        y1 = h - crop_size
    
    # クロップ実行
    cropped = image.crop((x1, y1, x1 + crop_size, y1 + crop_size))
    
    return cropped


def process_image(
    input_path: Path,
    output_path: Path,
    target_size: int | None = None
) -> bool:
    """
    単一画像を処理：顔検出→中心クロップ→保存
    
    Args:
        input_path: 入力画像パス
        output_path: 出力画像パス
        target_size: 出力サイズ（None=クロップサイズのまま）
        
    Returns:
        成功したかどうか
    """
    try:
        # 画像読み込み
        image = Image.open(input_path)
        
        # EXIF回転情報を適用
        image = ImageOps.exif_transpose(image)
        
        # 顔検出
        face_center = detect_face_center_gemini(image)
        
        if face_center is None:
            # 顔が検出できない場合は画像中心を使用
            w, h = image.size
            face_center = (w // 2, h // 2)
            logger.warning(f"No face detected, using image center: {input_path.name}")
        else:
            logger.info(f"Face detected at {face_center}: {input_path.name}")
        
        # 正方形クロップ（短辺サイズ）
        cropped = crop_square_around_center(image, face_center)
        
        # リサイズ（指定がある場合）
        if target_size is not None:
            cropped = cropped.resize((target_size, target_size), Image.Resampling.LANCZOS)
        
        # 出力ディレクトリ作成
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存（品質を高く設定）
        if output_path.suffix.lower() in {".jpg", ".jpeg"}:
            # RGBに変換（RGBAの場合）
            if cropped.mode == "RGBA":
                cropped = cropped.convert("RGB")
            cropped.save(output_path, quality=95)
        else:
            cropped.save(output_path)
        
        logger.info(f"Saved: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error processing {input_path}: {e}")
        return False


def process_directory(
    input_dir: Path,
    output_dir: Path,
    target_size: int | None = None
) -> tuple[int, int]:
    """
    ディレクトリ内の全画像を処理
    
    Args:
        input_dir: 入力ディレクトリ
        output_dir: 出力ディレクトリ
        target_size: 出力サイズ
        
    Returns:
        (成功数, 失敗数)
    """
    success_count = 0
    fail_count = 0
    
    # 対象ファイルを収集
    image_files = [
        f for f in input_dir.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    
    logger.info(f"Found {len(image_files)} images in {input_dir}")
    
    for img_path in image_files:
        output_path = output_dir / img_path.name
        
        if process_image(img_path, output_path, target_size):
            success_count += 1
        else:
            fail_count += 1
    
    return success_count, fail_count


def main():
    """CLI エントリーポイント"""
    parser = argparse.ArgumentParser(
        description="顔検出を使った1:1クロップツール（Gemini API使用）"
    )
    parser.add_argument(
        "input",
        type=str,
        help="入力画像またはディレクトリのパス"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="出力先（デフォルト: 入力ディレクトリ/1x1）"
    )
    parser.add_argument(
        "-s", "--size",
        type=int,
        default=None,
        help="出力サイズ（例: 1024）。指定しない場合はクロップサイズのまま"
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    
    if not input_path.exists():
        logger.error(f"Input path does not exist: {input_path}")
        return 1
    
    if input_path.is_file():
        # 単一ファイル処理
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = input_path.parent / "1x1" / input_path.name
        
        success = process_image(input_path, output_path, args.size)
        return 0 if success else 1
        
    elif input_path.is_dir():
        # ディレクトリ処理
        if args.output:
            output_dir = Path(args.output)
        else:
            output_dir = input_path / "1x1"
        
        success, fail = process_directory(input_path, output_dir, args.size)
        logger.info(f"Completed: {success} success, {fail} failed")
        return 0 if fail == 0 else 1
    
    else:
        logger.error(f"Invalid input path: {input_path}")
        return 1


if __name__ == "__main__":
    exit(main())
