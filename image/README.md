# image - Gemini 画像生成

Gemini API（`gemini-3-pro-image-preview`）を使った画像生成バッチツール。

## 機能

- **テキストから画像生成**: 日本語プロンプトで画像を生成
- **参照画像を使った生成**: 最大14枚の画像を入力し、スタイルやキャラクターを参照
- **プレースホルダー**: `{0}`, `{1}`, ... でプロンプト内に画像を挿入

## セットアップ

### 環境変数

`.env` に以下を設定:

```env
GOOGLE_API_KEY=your_google_api_key
```

### 依存パッケージ

```powershell
pip install google-genai pillow
```

## 使い方

### CLI

```powershell
python -m image.batch_imagen --csv path/to/jobs.csv
```

### F5 実行（IDE）

引数なしで実行すると、ファイルダイアログでCSVを選択。

## CSV仕様

| 列名 | 必須 | 説明 |
|------|------|------|
| `output_dir` | - | 出力先フォルダ（絶対パス） |
| `output_filename` | - | 出力ファイル名（拡張子なし） |
| `prompt` | ✅ | 生成指示（日本語OK） |
| `ref_images` | - | 参照画像パス（セミコロン区切り、最大14枚） |
| `aspect_ratio` | - | アスペクト比（1:1, 16:9, 9:16, 4:3, 3:4）デフォルト 1:1 |
| `resolution` | - | 出力解像度（1K, 2K, 4K）デフォルト 1K |
| `number_of_images` | - | 生成枚数（デフォルト1） |

### プレースホルダー

`prompt` 内で `{0}`, `{1}`, ... を使うと、`ref_images` の対応する画像がその位置に挿入される。

```csv
prompt,ref_images
"{0}のキャラクターを{1}のスタイルで描いて",cat.png;style.png
```

→ API入力: `[cat.png, "のキャラクターを", style.png, "のスタイルで描いて"]`

## Tips

### 背景について

- **透明背景は生成できない**: Gemini の画像生成は透明背景（PNG alpha）をサポートしていません
- **単色背景を推奨**: 白背景や単色背景を指定すると、後から背景除去ツールで処理しやすくなります
- プロンプト例: `「背景は白の単色で」`、`「背景は薄いグレーで」`

### キャラクター素材を作る場合

```
{0}のキャラクターデザインを参考に、同じキャラクターが〇〇しているポーズを描いてください。
背景は白の単色で、キャラクター素材として使えるようにしてください。
```

## サンプル

`samples/` ディレクトリにサンプルCSVあり:

- `imagen_jobs_sample.csv` - テキストのみ
- `imagen_jobs_sample_ref.csv` - 参照画像あり（プレースホルダー使用）

## ファイル構成

```
image/
├── README.md           # このファイル
├── __init__.py
├── conf.py             # 設定（環境変数読み込み）
├── imagen_client.py    # Gemini API クライアント
├── batch_imagen.py     # バッチ実行スクリプト
└── samples/            # サンプルCSV・画像
```

