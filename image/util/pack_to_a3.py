"""
複数画像をA3用紙に最適配置するビンパッキングスクリプト

使用方法:
    python -m image.util.pack_to_a3 /path/to/image_folder
    python -m image.util.pack_to_a3 /path/to/image_folder --output /path/to/output
    python -m image.util.pack_to_a3  # ファイルダイアログで選択

動作:
    - フォルダ内の全画像を読み込み
    - 長方形パッキングアルゴリズムで最適配置を計算
    - A3サイズ（297mm x 420mm）に収めて出力
    - 収まらない場合は複数ページに分割
"""

import sys
import argparse
from pathlib import Path
from PIL import Image, ImageOps
from datetime import datetime

try:
    import rectpack
except ImportError:
    print("[ERROR] rectpack is not installed. Run: pip install rectpack")
    sys.exit(1)

# A3サイズ（mm）
A3_WIDTH_MM = 420   # 横向き
A3_HEIGHT_MM = 297

# 1インチ = 25.4mm
MM_PER_INCH = 25.4

# 基準DPI
BASE_DPI = 300

# 画像間のマージン（px）
MARGIN_PX = 10

# 対応する画像拡張子
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif'}


def mm_to_px(mm: float, dpi: float = BASE_DPI) -> int:
    """ミリメートルをピクセルに変換"""
    return int(mm / MM_PER_INCH * dpi)


def get_a3_size_px(dpi: float = BASE_DPI) -> tuple[int, int]:
    """A3サイズをピクセルで取得（横向き）"""
    return mm_to_px(A3_WIDTH_MM, dpi), mm_to_px(A3_HEIGHT_MM, dpi)


def load_images(folder: Path) -> list[tuple[Path, Image.Image, tuple[int, int]]]:
    """
    フォルダ内の画像を読み込む
    
    Returns:
        [(path, image, (width, height)), ...]
    """
    images = []
    
    for file in sorted(folder.iterdir()):
        if file.suffix.lower() in IMAGE_EXTENSIONS:
            try:
                img = Image.open(file)
                # EXIF Orientationに基づいて画像を正しい向きに回転
                img = ImageOps.exif_transpose(img)
                images.append((file, img, img.size))
                print(f"[LOAD] {file.name}: {img.size[0]}x{img.size[1]}")
            except Exception as e:
                print(f"[SKIP] {file.name}: {e}")
    
    print(f"[INFO] Loaded {len(images)} images")
    return images


def calculate_scale_factor(images: list[tuple[Path, Image.Image, tuple[int, int]]],
                          canvas_w: int, canvas_h: int,
                          margin: int = MARGIN_PX) -> float:
    """
    全画像がキャンバスに収まるスケールファクターを二分探索で計算
    
    Args:
        images: 画像リスト
        canvas_w: キャンバス幅
        canvas_h: キャンバス高さ
        margin: 画像間マージン
    
    Returns:
        最適なスケールファクター（0.0 ~ 1.0）
    """
    def can_pack(scale: float) -> bool:
        """指定スケールで全画像がパック可能かチェック"""
        packer = rectpack.newPacker(rotation=False)
        packer.add_bin(canvas_w, canvas_h)
        
        for path, img, (w, h) in images:
            scaled_w = max(1, int(w * scale) + margin)
            scaled_h = max(1, int(h * scale) + margin)
            packer.add_rect(scaled_w, scaled_h, rid=path)
        
        packer.pack()
        # packer.rect_list()は(b, x, y, w, h, rid)のタプルリストを返す
        return len(packer.rect_list()) == len(images)
    
    # 二分探索でスケールファクターを決定
    low, high = 0.01, 1.0
    best_scale = low
    
    for _ in range(50):  # 十分な精度を確保
        mid = (low + high) / 2
        if can_pack(mid):
            best_scale = mid
            low = mid
        else:
            high = mid
    
    return best_scale


def pack_images_multi_page(images: list[tuple[Path, Image.Image, tuple[int, int]]],
                           canvas_w: int, canvas_h: int,
                           margin: int = MARGIN_PX,
                           min_scale: float = 0.1) -> list[list[tuple[Path, Image.Image, int, int, int, int]]]:
    """
    複数ページに分割してパッキング
    
    Args:
        images: 画像リスト
        canvas_w: キャンバス幅
        canvas_h: キャンバス高さ
        margin: 画像間マージン
        min_scale: 最小スケール（これ以下なら分割）
    
    Returns:
        ページごとの配置リスト [(path, img, x, y, w, h), ...]
    """
    # まず1ページに収めてみる
    scale = calculate_scale_factor(images, canvas_w, canvas_h, margin)
    print(f"[INFO] Calculated scale factor: {scale:.4f}")
    
    if scale >= min_scale:
        # 1ページに収まる
        result = pack_single_page(images, canvas_w, canvas_h, scale, margin)
        if result:
            return [result]
    
    # 分割が必要 - 画像サイズの大きい順にソートして順次パック
    sorted_images = sorted(images, key=lambda x: x[2][0] * x[2][1], reverse=True)
    pages = []
    remaining = list(sorted_images)
    
    while remaining:
        # このページに入る画像を探す
        page_images = []
        still_remaining = []
        
        for item in remaining:
            test_images = page_images + [item]
            test_scale = calculate_scale_factor(test_images, canvas_w, canvas_h, margin)
            
            if test_scale >= min_scale:
                page_images.append(item)
            else:
                still_remaining.append(item)
        
        if not page_images:
            # 1枚も入らない場合は強制的に1枚入れる
            page_images = [remaining[0]]
            still_remaining = remaining[1:]
        
        # このページをパック
        page_scale = calculate_scale_factor(page_images, canvas_w, canvas_h, margin)
        result = pack_single_page(page_images, canvas_w, canvas_h, page_scale, margin)
        if result:
            pages.append(result)
        
        remaining = still_remaining
    
    return pages


def pack_single_page(images: list[tuple[Path, Image.Image, tuple[int, int]]],
                     canvas_w: int, canvas_h: int,
                     scale: float,
                     margin: int = MARGIN_PX) -> list[tuple[Path, Image.Image, int, int, int, int]] | None:
    """
    1ページ分のパッキングを実行
    
    Returns:
        [(path, img, x, y, scaled_w, scaled_h), ...] or None
    """
    packer = rectpack.newPacker(rotation=False)
    packer.add_bin(canvas_w, canvas_h)
    
    # 画像IDとスケール済みサイズのマッピング
    rect_data = {}
    for path, img, (w, h) in images:
        scaled_w = max(1, int(w * scale))
        scaled_h = max(1, int(h * scale))
        rect_data[id(path)] = (path, img, scaled_w, scaled_h, w, h)
        packer.add_rect(scaled_w + margin, scaled_h + margin, rid=id(path))
    
    packer.pack()
    
    # packer.rect_list()は(b, x, y, w, h, rid)のリストを返す
    rects = packer.rect_list()
    if len(rects) != len(images):
        return None
    
    result = []
    for b, x, y, w, h, rid in rects:
        path, img, scaled_w, scaled_h, orig_w, orig_h = rect_data[rid]
        
        # 回転の検出と補正
        expected_w, expected_h = scaled_w + margin, scaled_h + margin
        if (w, h) == (expected_h, expected_w):
            # 回転された場合
            img = img.rotate(90, expand=True)
            scaled_w, scaled_h = scaled_h, scaled_w
        
        result.append((path, img, x, y, scaled_w, scaled_h))
    
    return result


def render_page(placements: list[tuple[Path, Image.Image, int, int, int, int]],
                canvas_w: int, canvas_h: int) -> Image.Image:
    """
    パッキング結果をレンダリング
    
    Args:
        placements: 配置リスト [(path, img, x, y, w, h), ...]
        canvas_w: キャンバス幅
        canvas_h: キャンバス高さ
    
    Returns:
        レンダリング済み画像
    """
    canvas = Image.new("RGB", (canvas_w, canvas_h), color=(255, 255, 255))
    
    for path, img, x, y, w, h in placements:
        # RGBA→RGB変換
        if img.mode == "RGBA":
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3])
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")
        
        # リサイズ
        resized = img.resize((w, h), Image.Resampling.LANCZOS)
        canvas.paste(resized, (x, y))
        print(f"  [PLACE] {path.name}: ({x}, {y}) @ {w}x{h}")
    
    return canvas


def select_folder_dialog() -> tuple[Path, Path] | None:
    """ファイルダイアログでフォルダを選択"""
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        root = tk.Tk()
        root.withdraw()
        
        # 入力フォルダ選択
        input_folder = filedialog.askdirectory(title="Select image folder")
        if not input_folder:
            return None
        
        # 出力フォルダ選択
        output_folder = filedialog.askdirectory(title="Select output folder")
        if not output_folder:
            # デフォルトは入力フォルダと同じ場所
            output_folder = input_folder
        
        return Path(input_folder), Path(output_folder)
    
    except Exception as e:
        print(f"[ERROR] Dialog failed: {e}")
        return None


def parse_args() -> argparse.Namespace:
    """コマンドライン引数をパース"""
    parser = argparse.ArgumentParser(
        description="Pack multiple images into A3 sheets"
    )
    parser.add_argument("input", nargs="?", help="Input folder containing images")
    parser.add_argument("-o", "--output", help="Output folder (default: same as input)")
    parser.add_argument("-d", "--dpi", type=int, default=BASE_DPI,
                        help=f"Output DPI (default: {BASE_DPI})")
    parser.add_argument("-m", "--margin", type=int, default=MARGIN_PX,
                        help=f"Margin between images in px (default: {MARGIN_PX})")
    parser.add_argument("--min-scale", type=float, default=0.1,
                        help="Minimum scale factor before splitting pages (default: 0.1)")
    return parser.parse_args()


def main():
    args = parse_args()
    
    if args.input:
        input_folder = Path(args.input)
        output_folder = Path(args.output) if args.output else input_folder
    else:
        result = select_folder_dialog()
        if result is None:
            print("[INFO] Cancelled.")
            return
        input_folder, output_folder = result
    
    if not input_folder.exists():
        print(f"[ERROR] Folder not found: {input_folder}")
        sys.exit(1)
    
    # 画像を読み込み
    images = load_images(input_folder)
    if not images:
        print("[ERROR] No images found in folder")
        sys.exit(1)
    
    # A3サイズ取得
    canvas_w, canvas_h = get_a3_size_px(args.dpi)
    print(f"[INFO] A3 canvas: {canvas_w} x {canvas_h} px ({args.dpi} DPI)")
    
    # パッキング実行
    print("[INFO] Packing images...")
    pages = pack_images_multi_page(
        images, canvas_w, canvas_h,
        margin=args.margin,
        min_scale=args.min_scale
    )
    
    print(f"[INFO] Generated {len(pages)} page(s)")
    
    # 出力
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_folder.mkdir(parents=True, exist_ok=True)
    
    for i, placements in enumerate(pages, 1):
        print(f"[INFO] Rendering page {i}/{len(pages)}...")
        canvas = render_page(placements, canvas_w, canvas_h)
        
        if len(pages) == 1:
            output_path = output_folder / f"packed_a3_{timestamp}.png"
        else:
            output_path = output_folder / f"packed_a3_{timestamp}_page{i:02d}.png"
        
        canvas.save(output_path, quality=95, dpi=(args.dpi, args.dpi))
        print(f"[OK] Saved: {output_path}")
    
    print(f"[DONE] Successfully packed {len(images)} images into {len(pages)} A3 sheet(s)")


if __name__ == "__main__":
    main()

