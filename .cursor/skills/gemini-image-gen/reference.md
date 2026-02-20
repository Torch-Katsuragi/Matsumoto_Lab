# CSV 仕様リファレンス

## CSV 列定義

| 列名 | 必須 | 説明 |
|---|---|---|
| `prompt` | 必須 | 画像生成プロンプト。`{0}`, `{1}` で参照画像を挿入可能 |
| `ref_images` | 任意 | 参照画像パス（セミコロン `;` 区切り、最大14枚）。相対パスは CSV 基準 |
| `output_dir` | 任意 | 出力先フォルダ（絶対パス）。省略時は `Downloads/generated_image/<timestamp>` |
| `output_filename` | 任意 | 出力ファイル名（拡張子なし）。省略時はプロンプトや参照画像名から自動生成 |
| `aspect_ratio` | 任意 | `1:1`, `16:9`, `9:16`, `4:3`, `3:4`。デフォルト `1:1` |
| `resolution` | 任意 | `1K`, `2K`, `4K`。デフォルト `1K` |
| `number_of_images` | 任意 | 生成枚数。デフォルト `1` |
| `seed` | 任意 | 乱数シード（将来用） |

## サンプル CSV

### テキストのみ

```csv
output_dir,output_filename,prompt,ref_images,aspect_ratio,resolution,number_of_images,seed
,,水彩画風のかわいいロボット,,1:1,1K,1,
,,空飛ぶ車がある未来都市の夕焼け,,16:9,2K,1,42
```

### 参照画像あり

```csv
prompt,ref_images,aspect_ratio,resolution
{0}のキャラクターを宇宙服姿で描いてください,images/cat.png,1:1,1K
{0}のスタイルで未来都市を描いてください,images/landscape.png,16:9,2K
{0}を{1}の風景の中に配置してください,images/cat.png;images/landscape.png,16:9,2K
```

## プレースホルダー

プロンプト内で `{0}`, `{1}`, ... を使うと、`ref_images` の対応する画像がその位置に挿入される。

- `{0}` → 1番目の参照画像
- `{1}` → 2番目の参照画像

プレースホルダーがない場合、参照画像はプロンプトの前にすべて配置される。

## ファイル名の自動生成ルール

1. `output_filename` が指定されている場合: そのまま使用
2. `ref_images` がある場合: 最初の参照画像のファイル名（拡張子なし）
3. テキストのみの場合: プロンプト先頭20文字（ファイル名禁止文字で切断）

同名ファイルが既に存在する場合は `_00001` のような連番が付与される。

## ログフォーマット (JSONL)

バッチ実行時、出力ディレクトリに `imagen_batch_log.jsonl` が生成される。各行は以下の構造:

```json
{
  "time": "2026-01-01T00:00:00+00:00",
  "row_index": 1,
  "status": "ok",
  "output_files": ["path/to/output.png"],
  "error": null,
  "request": {"prompt": "...", "ref_images": "..."},
  "parsed_request": {"prompt": "...", "aspect_ratio": "1:1", "resolution": "1K"}
}
```

`status` は `ok`, `error`, `dry_run`, `skipped` のいずれか。

## 環境変数

| 変数名 | 説明 |
|---|---|
| `GOOGLE_API_KEY` | Gemini API キー（必須） |
| `IMAGEN_MODEL` | モデル名の上書き（任意） |
