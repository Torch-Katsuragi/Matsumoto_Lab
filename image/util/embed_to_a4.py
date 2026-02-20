"""
任意の画像をA4用紙の中心に任意サイズで埋め込むスクリプト

使用方法:
    python -m image.util.embed_to_a4 input.png output.png
    python -m image.util.embed_to_a4 input.png output.png --width 100 --height 80
    python -m image.util.embed_to_a4  # ファイルダイアログで選択

動作:
    - 画像を指定サイズ（デフォルト150mm x 150mm）でA4用紙(210mm x 297mm)の中央に配置
    - 画像は「cover」方式でリサイズ: 指定領域を完全に埋め、はみ出し部分はクロップ
    - DPI情報が画像メタデータに埋め込まれるため、印刷時に正確なサイズで出力可能
"""

import sys
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# A4サイズ（mm）
A4_WIDTH_MM = 210
A4_HEIGHT_MM = 297

# デフォルトの埋め込みサイズ（mm）
DEFAULT_WIDTH_MM = 150
DEFAULT_HEIGHT_MM = 150

# 1インチ = 25.4mm
MM_PER_INCH = 25.4

# 基準DPI（300DPIを基準にA4キャンバスを作成）
BASE_DPI = 300


def crop_and_resize_cover(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """
    Cover方式で画像をリサイズ＆クロップ
    ターゲット領域を完全に埋め、はみ出し部分は中心基準でクロップする
    
    Args:
        img: 入力画像
        target_w: 目標幅（px）
        target_h: 目標高さ（px）
    
    Returns:
        リサイズ＆クロップ済み画像
    """
    src_w, src_h = img.size
    src_ratio = src_w / src_h
    target_ratio = target_w / target_h
    
    if src_ratio > target_ratio:
        # 画像の方が横長 → 高さを合わせて左右をクロップ
        new_h = src_h
        new_w = int(src_h * target_ratio)
        left = (src_w - new_w) // 2
        crop_box = (left, 0, left + new_w, new_h)
    else:
        # 画像の方が縦長 → 幅を合わせて上下をクロップ
        new_w = src_w
        new_h = int(src_w / target_ratio)
        top = (src_h - new_h) // 2
        crop_box = (0, top, new_w, top + new_h)
    
    # クロップしてからリサイズ
    cropped = img.crop(crop_box)
    return cropped.resize((target_w, target_h), Image.Resampling.LANCZOS)


def calculate_dimensions(width_mm: float, height_mm: float, dpi: float) -> tuple[int, int, int, int]:
    """
    指定サイズとDPIからA4キャンバスと埋め込みサイズをpxで計算
    
    Args:
        width_mm: 埋め込み幅（mm）
        height_mm: 埋め込み高さ（mm）
        dpi: 解像度
    
    Returns:
        (a4_width_px, a4_height_px, embed_width_px, embed_height_px)
    """
    # A4キャンバスサイズ（px）
    a4_width_px = int(A4_WIDTH_MM / MM_PER_INCH * dpi)
    a4_height_px = int(A4_HEIGHT_MM / MM_PER_INCH * dpi)
    
    # 埋め込みサイズ（px）
    embed_width_px = int(width_mm / MM_PER_INCH * dpi)
    embed_height_px = int(height_mm / MM_PER_INCH * dpi)
    
    return a4_width_px, a4_height_px, embed_width_px, embed_height_px


def get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """システムフォントを取得（日本語対応）"""
    # Windowsの日本語フォントを優先的に試行
    font_candidates = [
        "C:/Windows/Fonts/meiryo.ttc",      # メイリオ
        "C:/Windows/Fonts/msgothic.ttc",    # MSゴシック
        "C:/Windows/Fonts/YuGothM.ttc",     # 游ゴシック
        "C:/Windows/Fonts/arial.ttf",       # Arial（英語フォールバック）
    ]
    for font_path in font_candidates:
        try:
            return ImageFont.truetype(font_path, size)
        except (OSError, IOError):
            continue
    # すべて失敗したらデフォルトフォント
    return ImageFont.load_default()


def embed_to_a4(input_path: Path, output_path: Path, 
               width_mm: float = DEFAULT_WIDTH_MM, 
               height_mm: float = DEFAULT_HEIGHT_MM,
               show_filename: bool = False) -> None:
    """
    任意の画像をA4用紙の中心に指定サイズで埋め込む
    
    Args:
        input_path: 入力画像パス
        output_path: 出力画像パス
        width_mm: 埋め込み幅（mm）
        height_mm: 埋め込み高さ（mm）
        show_filename: 下部余白にファイル名を表示するか
    """
    # 入力画像を読み込み
    img = Image.open(input_path)
    src_w, src_h = img.size
    print(f"[INFO] Input: {src_w} x {src_h} px")
    
    # A4キャンバスと埋め込みサイズを計算
    a4_w, a4_h, embed_w, embed_h = calculate_dimensions(width_mm, height_mm, BASE_DPI)
    print(f"[INFO] A4 canvas: {a4_w} x {a4_h} px ({BASE_DPI} DPI)")
    print(f"[INFO] Embed size: {embed_w} x {embed_h} px ({width_mm}mm x {height_mm}mm)")
    
    # RGBA処理：白背景に合成
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    
    # Cover方式でリサイズ＆クロップ
    resized = crop_and_resize_cover(img, embed_w, embed_h)
    
    # 白背景のA4キャンバスを作成
    canvas = Image.new("RGB", (a4_w, a4_h), color=(255, 255, 255))
    
    # 中央に配置
    x = (a4_w - embed_w) // 2
    y = (a4_h - embed_h) // 2
    canvas.paste(resized, (x, y))
    
    # ファイル名を下部余白に描画
    if show_filename:
        draw = ImageDraw.Draw(canvas)
        filename = input_path.stem  # 拡張子なしのファイル名
        
        # 画像の下端とA4の下端の中間にテキストを配置
        img_bottom = y + embed_h
        margin_height = a4_h - img_bottom
        
        # フォントサイズを余白に収まるように調整（余白の40%程度）
        font_size = min(int(margin_height * 0.4), 60)
        font = get_font(font_size)
        
        # テキストのバウンディングボックスを取得
        bbox = draw.textbbox((0, 0), filename, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        # 中央揃えで、画像下端と用紙下端の中間に配置
        text_x = (a4_w - text_w) // 2
        text_y = img_bottom + (margin_height - text_h) // 2
        
        draw.text((text_x, text_y), filename, fill=(0, 0, 0), font=font)
        print(f"[INFO] Added filename: {filename}")
    
    # DPI情報を埋め込んで保存
    canvas.save(output_path, quality=95, dpi=(BASE_DPI, BASE_DPI))
    print(f"[OK] Saved: {output_path}")
    print(f"[INFO] Print size: {width_mm}mm x {height_mm}mm")


def select_file_dialog() -> tuple[Path, Path, float, float] | None:
    """ファイルダイアログで入出力ファイルとサイズを選択"""
    try:
        import tkinter as tk
        from tkinter import filedialog, simpledialog
        
        root = tk.Tk()
        root.withdraw()
        
        # 入力ファイル選択
        input_path = filedialog.askopenfilename(
            title="Select input image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.webp"),
                ("All files", "*.*")
            ]
        )
        if not input_path:
            return None
        
        # サイズ入力
        width = simpledialog.askfloat("Width", "Embed width (mm):", 
                                      initialvalue=DEFAULT_WIDTH_MM, minvalue=1, maxvalue=200)
        if width is None:
            return None
        
        height = simpledialog.askfloat("Height", "Embed height (mm):", 
                                       initialvalue=DEFAULT_HEIGHT_MM, minvalue=1, maxvalue=290)
        if height is None:
            return None
        
        # 出力ファイル選択
        input_p = Path(input_path)
        default_output = input_p.stem + "_a4" + input_p.suffix
        
        output_path = filedialog.asksaveasfilename(
            title="Save A4 image as",
            defaultextension=input_p.suffix,
            initialfile=default_output,
            filetypes=[
                ("PNG", "*.png"),
                ("JPEG", "*.jpg *.jpeg"),
                ("All files", "*.*")
            ]
        )
        if not output_path:
            return None
        
        return Path(input_path), Path(output_path), width, height
    
    except Exception as e:
        print(f"[ERROR] Dialog failed: {e}")
        return None


def parse_args() -> argparse.Namespace:
    """コマンドライン引数をパース"""
    parser = argparse.ArgumentParser(
        description="Embed image to A4 with cover-fit cropping"
    )
    parser.add_argument("input", nargs="?", help="Input image path")
    parser.add_argument("output", nargs="?", help="Output image path")
    parser.add_argument("-W", "--width", type=float, default=DEFAULT_WIDTH_MM,
                        help=f"Embed width in mm (default: {DEFAULT_WIDTH_MM})")
    parser.add_argument("-H", "--height", type=float, default=DEFAULT_HEIGHT_MM,
                        help=f"Embed height in mm (default: {DEFAULT_HEIGHT_MM})")
    parser.add_argument("-n", "--name", action="store_true",
                        help="Show filename in the bottom margin")
    return parser.parse_args()


def main():
    args = parse_args()
    
    if args.input:
        # コマンドライン引数から
        input_path = Path(args.input)
        output_path = Path(args.output) if args.output else \
                      input_path.parent / (input_path.stem + "_a4" + input_path.suffix)
        width_mm, height_mm = args.width, args.height
        show_filename = args.name
    else:
        # ファイルダイアログ
        result = select_file_dialog()
        if result is None:
            print("[INFO] Cancelled.")
            return
        input_path, output_path, width_mm, height_mm = result
        show_filename = False  # ダイアログモードではデフォルトOFF
    
    if not input_path.exists():
        print(f"[ERROR] File not found: {input_path}")
        sys.exit(1)
    
    embed_to_a4(input_path, output_path, width_mm, height_mm, show_filename)


if __name__ == "__main__":
    main()




