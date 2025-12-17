"""
正方形画像をA4用紙の中心に埋め込むスクリプト

使用方法:
    python -m image.util.embed_to_a4 input.png output.png
    python -m image.util.embed_to_a4  # ファイルダイアログで選択

動作:
    - 入力画像を15cm x 15cmとして扱い、A4用紙(210mm x 297mm)の中央に配置
    - 入力画像のサイズに応じてDPIが決定される（1024px → 173DPI）
    - DPI情報が画像メタデータに埋め込まれるため、印刷時に正確なサイズで出力可能
"""

import sys
from pathlib import Path
from PIL import Image

# A4サイズ（mm）
A4_WIDTH_MM = 210
A4_HEIGHT_MM = 297

# 埋め込む正方形のサイズ（mm）
TARGET_SIZE_MM = 150

# 1インチ = 25.4mm
MM_PER_INCH = 25.4


def calculate_dimensions(input_size_px: int) -> tuple[int, int, int, float]:
    """
    入力画像サイズからA4キャンバスと配置サイズを計算
    
    Args:
        input_size_px: 入力正方形画像の一辺（px）
    
    Returns:
        (a4_width_px, a4_height_px, embed_size_px, effective_dpi)
    """
    # 入力画像を TARGET_SIZE_MM として扱い、DPIを逆算
    # DPI = px / inch = px / (mm / 25.4)
    target_inch = TARGET_SIZE_MM / MM_PER_INCH
    effective_dpi = input_size_px / target_inch
    
    # そのDPIでA4サイズを計算
    a4_width_px = int(A4_WIDTH_MM / MM_PER_INCH * effective_dpi)
    a4_height_px = int(A4_HEIGHT_MM / MM_PER_INCH * effective_dpi)
    
    print(f"[INFO] Input size: {input_size_px}px")
    print(f"[INFO] Effective DPI: {effective_dpi:.1f}")
    print(f"[INFO] A4 canvas: {a4_width_px} x {a4_height_px} px")
    
    return a4_width_px, a4_height_px, input_size_px, effective_dpi


def embed_to_a4(input_path: Path, output_path: Path) -> None:
    """
    正方形画像をA4用紙の中心に埋め込む
    
    Args:
        input_path: 入力画像パス
        output_path: 出力画像パス
    """
    # 入力画像を読み込み
    img = Image.open(input_path)
    width, height = img.size
    
    # 正方形チェック（許容誤差5%）
    ratio = max(width, height) / min(width, height)
    if ratio > 1.05:
        print(f"[WARN] Image is not square: {width}x{height} (ratio: {ratio:.2f})")
        print(f"[WARN] Using the smaller dimension: {min(width, height)}px")
    
    # 小さい方を基準にする（正方形でない場合も対応）
    base_size = min(width, height)
    
    # A4キャンバスサイズを計算
    a4_width, a4_height, embed_size, dpi = calculate_dimensions(base_size)
    
    # 白背景のA4キャンバスを作成
    canvas = Image.new("RGB", (a4_width, a4_height), color=(255, 255, 255))
    
    # 入力画像がRGBAの場合、白背景に合成
    if img.mode == "RGBA":
        # 白背景に合成
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])  # アルファチャンネルをマスクとして使用
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    
    # 中心座標を計算
    x = (a4_width - width) // 2
    y = (a4_height - height) // 2
    
    # 画像を貼り付け
    canvas.paste(img, (x, y))
    
    # DPI情報を埋め込んで保存（印刷時に正確なサイズで出力される）
    dpi_int = int(round(dpi))
    canvas.save(output_path, quality=95, dpi=(dpi_int, dpi_int))
    print(f"[OK] Saved: {output_path}")
    print(f"[INFO] Embedded DPI: {dpi_int}")
    print(f"[INFO] Print size: {TARGET_SIZE_MM}mm x {TARGET_SIZE_MM}mm")


def select_file_dialog() -> tuple[Path, Path] | None:
    """ファイルダイアログで入出力ファイルを選択"""
    try:
        import tkinter as tk
        from tkinter import filedialog
        
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
        
        return Path(input_path), Path(output_path)
    
    except Exception as e:
        print(f"[ERROR] Dialog failed: {e}")
        return None


def main():
    if len(sys.argv) >= 3:
        # コマンドライン引数から
        input_path = Path(sys.argv[1])
        output_path = Path(sys.argv[2])
    elif len(sys.argv) == 2:
        # 入力のみ指定、出力は自動生成
        input_path = Path(sys.argv[1])
        output_path = input_path.parent / (input_path.stem + "_a4" + input_path.suffix)
    else:
        # ファイルダイアログ
        result = select_file_dialog()
        if result is None:
            print("[INFO] Cancelled.")
            return
        input_path, output_path = result
    
    if not input_path.exists():
        print(f"[ERROR] File not found: {input_path}")
        sys.exit(1)
    
    embed_to_a4(input_path, output_path)


if __name__ == "__main__":
    main()




