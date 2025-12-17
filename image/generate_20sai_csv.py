"""
20歳の顔展用のCSV生成スクリプト
"""

import csv
from pathlib import Path

# 入力フォルダ
INPUT_DIR = Path(r"I:\マイドライブ\20歳の顔展\写真\inbox\大人")
# 出力フォルダ
OUTPUT_DIR = INPUT_DIR / "restored_4k"
# CSV出力先
CSV_PATH = Path(__file__).parent / "20sai_restore.csv"

# 対象拡張子
IMAGE_EXTS = {".jpg", ".jpeg", ".png"}

# プロンプト（元画像を維持、高画質化、カラー化、映り込み除外）
PROMPT = """{0}を現代の高性能デジタルカメラで撮影したかのような高画質画像として再生成してください。

重要な指示:
- 被写体の人物の顔、表情、服装、ポーズを忠実に再現すること
- 背景もできるだけ元の写真を維持すること
- 被写体以外に映り込んでいる人物がいれば除外すること
- 白黒写真の場合は自然なカラーで再生成すること
- 画質、解像度、鮮明さを大幅に向上させること
- 自然な肌の質感と照明を再現すること"""


def main():
    # 出力フォルダ作成
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 直下の画像ファイルのみ取得（サブフォルダ除外）
    images = [f for f in INPUT_DIR.iterdir() 
              if f.is_file() and f.suffix.lower() in IMAGE_EXTS]
    images.sort(key=lambda x: x.name)
    
    print(f"Found {len(images)} images")
    
    # CSV生成
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "output_dir", "output_filename", "prompt", 
            "ref_images", "aspect_ratio", "resolution", "number_of_images", "seed"
        ])
        
        for img in images:
            output_name = img.stem + "_restored"
            writer.writerow([
                str(OUTPUT_DIR),
                output_name,
                PROMPT,
                str(img),
                "3:4",
                "4K",
                1,
                ""
            ])
            print(f"  - {img.name} -> {output_name}.png")
    
    print(f"\nCSV saved: {CSV_PATH}")
    print(f"Output dir: {OUTPUT_DIR}")
    print(f"\nRun with:")
    print(f"  python -m image.batch_imagen --csv \"{CSV_PATH}\"")


if __name__ == "__main__":
    main()

