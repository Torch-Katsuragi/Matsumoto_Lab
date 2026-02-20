---
name: gemini-image-gen
description: Gemini API (google-genai) を使った画像生成を行う。テキストから画像生成(t2i)、参照画像を使った画像変換(i2i)、CSVバッチ処理に対応。画像生成、Gemini画像、generate image、image generation、t2i、i2i と言及された場合に使用する。
---

# Gemini 画像生成

Gemini API (`google-genai`) を使ってテキストや参照画像から画像を生成する。

## 前提条件

```bash
pip install google-genai Pillow python-dotenv
```

`.env` または環境変数に `GOOGLE_API_KEY` を設定する:

```
GOOGLE_API_KEY=your_api_key_here
```

## 単発生成

### Python API

```python
from gemini_imagen import ImagenClient, ImagenRequest

client = ImagenClient()
req = ImagenRequest(
    prompt="水彩画風のかわいいロボット",
    aspect_ratio="1:1",
    resolution="1K",
)
images = client.generate(req)  # List[bytes]

from pathlib import Path
Path("output.png").write_bytes(images[0])
```

### 参照画像を使う

```python
req = ImagenRequest(
    prompt="{0}のキャラクターを宇宙服姿で描いてください",
    ref_images=(Path("character.png"),),
    aspect_ratio="1:1",
)
```

プレースホルダー `{0}`, `{1}`, ... で参照画像の挿入位置を指定できる。
省略した場合は画像がプロンプトの前に配置される。

### CLI

```bash
python scripts/gemini_imagen.py --prompt "未来都市の夕焼け" --output out.png
python scripts/gemini_imagen.py --prompt "{0}をアニメ風に" --ref-images photo.jpg --output anime.png
```

## バッチ生成

CSV で複数の画像生成ジョブをまとめて実行する:

```bash
python scripts/batch_imagen.py --csv jobs.csv
```

引数なしで実行するとファイルダイアログで CSV を選択できる（Windows）。

### CSV 最小例

```csv
prompt,aspect_ratio
水彩画風のロボット,1:1
未来都市の夕焼け,16:9
```

### 主要オプション

| オプション | 説明 |
|---|---|
| `--csv` | 入力 CSV パス |
| `--limit N` | 先頭 N 行のみ処理 |
| `--dry-run` | API を呼ばずにパースだけ確認 |
| `--skip-existing` | 出力ファイルが既存ならスキップ |
| `--model` | モデル名（デフォルト: `gemini-2.0-flash-preview-image-generation`） |

## パラメータ一覧

| パラメータ | 値 | デフォルト |
|---|---|---|
| `aspect_ratio` | `1:1`, `16:9`, `9:16`, `4:3`, `3:4` | `1:1` |
| `resolution` | `1K`, `2K`, `4K` | `1K` |
| `number_of_images` | 整数 | `1` |
| `seed` | 整数（将来用） | なし |
| `ref_images` | 画像パス（セミコロン区切り、最大14枚） | なし |

## 詳細仕様

CSV 列の詳細やログフォーマットは [reference.md](reference.md) を参照。

## スクリプト

| ファイル | 用途 |
|---|---|
| `scripts/gemini_imagen.py` | 画像生成クライアント + 単発 CLI |
| `scripts/batch_imagen.py` | CSV バッチ処理 |
