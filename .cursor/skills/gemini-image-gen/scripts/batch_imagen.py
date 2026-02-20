"""
CSV から Gemini 画像生成ジョブをまとめて実行する（自己完結型）。

CSV 仕様:
  prompt(必須), ref_images, output_dir, output_filename,
  aspect_ratio, resolution, number_of_images, seed

必要パッケージ: google-genai, Pillow, python-dotenv(任意)
環境変数: GOOGLE_API_KEY（必須）
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import asdict
from typing import Dict, List, Set

# 同ディレクトリの gemini_imagen をインポート
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemini_imagen import ImagenClient, ImagenRequest  # noqa: E402


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timestamp_local() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _downloads_dir() -> Path:
    p = Path.home() / "Downloads"
    return p if p.exists() else Path.home()


_WIN_INVALID = set(r'\/:*?"<>|')


def _sanitize(s: str) -> str:
    out = "".join("_" if (ch in _WIN_INVALID or ord(ch) < 32) else ch for ch in s)
    return out.strip().strip(".") or "image"


def _basename_from_prompt(prompt: str, *, max_len: int = 20) -> str:
    buf: List[str] = []
    for ch in prompt.strip():
        if ch in _WIN_INVALID or ord(ch) < 32:
            break
        buf.append("_" if ch.isspace() else ch)
        if len(buf) >= max_len:
            break
    return _sanitize("".join(buf))


def _unique_path(dir_path: Path, base: str, *, row_index: int, used: Set[str]) -> Path:
    base = _sanitize(base)
    candidate = base
    if candidate in used or (dir_path / f"{candidate}.png").exists():
        candidate = f"{base}_{row_index:05d}"
    used.add(candidate)
    return dir_path / f"{candidate}.png"


def _to_int(x: str | None) -> int | None:
    s = str(x).strip() if x is not None else ""
    return int(s) if s else None


def _to_str(x: str | None) -> str | None:
    s = str(x).strip() if x is not None else ""
    return s or None


def _to_path(x: str | None) -> Path | None:
    s = _to_str(x)
    return Path(os.path.expandvars(s)) if s else None


def _resolve(p: Path | None, base: Path) -> Path | None:
    if p is None:
        return None
    return p if p.is_absolute() else (base / p).resolve()


# ---------------------------------------------------------------------------
# CSV パース・画像保存
# ---------------------------------------------------------------------------

def _parse_ref_images(raw: str | None, base_dir: Path) -> tuple[Path, ...]:
    if not raw:
        return ()
    paths = []
    for part in raw.split(";"):
        resolved = _resolve(_to_path(part), base_dir)
        if resolved:
            paths.append(resolved)
    return tuple(paths)


def _parse_row(row: Dict[str, str], *, base_dir: Path, validate: bool = True) -> ImagenRequest:
    prompt = _to_str(row.get("prompt"))
    if not prompt:
        raise ValueError("prompt が空です")
    ref_images = _parse_ref_images(row.get("ref_images"), base_dir)
    req = ImagenRequest(
        prompt=prompt,
        ref_images=ref_images,
        number_of_images=_to_int(row.get("number_of_images")) or 1,
        aspect_ratio=_to_str(row.get("aspect_ratio")) or "1:1",
        resolution=_to_str(row.get("resolution")) or "1K",
        seed=_to_int(row.get("seed")),
    )
    if validate:
        for p in req.ref_images:
            if not p.exists():
                raise FileNotFoundError(f"参照画像が見つかりません: {p}")
    return req


def _save_images(data_list: List[bytes], output_path: Path) -> List[Path]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if len(data_list) <= 1:
        output_path.write_bytes(data_list[0])
        return [output_path]
    written: List[Path] = []
    stem, suffix = output_path.stem, output_path.suffix or ".png"
    for i, b in enumerate(data_list, 1):
        p = output_path.with_name(f"{stem}_{i:02d}{suffix}")
        p.write_bytes(b)
        written.append(p)
    return written


def _write_log(lf, *, row_index: int, status: str, output_files: List[str] | None = None,
               error: str | None = None, request: Dict | None = None,
               parsed_request: Dict | None = None) -> None:
    payload = {
        "time": _now_iso(), "row_index": row_index, "status": status,
        "output_files": output_files or [], "error": error,
        "request": request or {}, "parsed_request": parsed_request,
    }
    lf.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    lf.flush()


# ---------------------------------------------------------------------------
# バッチ実行
# ---------------------------------------------------------------------------

def run_batch(csv_path: Path, *, model_name: str | None, dry_run: bool,
              limit: int | None, skip_existing: bool) -> int:
    csv_path = csv_path.resolve()
    base_dir = csv_path.parent
    out_dir = _downloads_dir() / "generated_image" / _timestamp_local()
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "imagen_batch_log.jsonl"

    client = None if dry_run else ImagenClient(model_name=model_name)
    ok = ng = 0
    used: Set[str] = set()

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f, \
         log_path.open("a", encoding="utf-8") as lf:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV にヘッダーがありません")

        for idx0, row in enumerate(reader):
            row_index = idx0 + 1
            if limit is not None and row_index > limit:
                break
            try:
                req = _parse_row(row, base_dir=base_dir, validate=not dry_run)

                # 出力先の決定
                explicit_dir = _to_str(row.get("output_dir"))
                row_dir = Path(explicit_dir) if explicit_dir else out_dir
                row_dir.mkdir(parents=True, exist_ok=True)

                explicit_name = _to_str(row.get("output_filename"))
                if explicit_name:
                    base_name = Path(explicit_name).stem
                elif req.ref_images:
                    base_name = req.ref_images[0].stem
                else:
                    base_name = _basename_from_prompt(req.prompt)

                output_path = _unique_path(row_dir, base_name, row_index=row_index, used=used)

                if skip_existing and output_path.exists():
                    logging.info("スキップ (既存): %s", output_path)
                    ok += 1
                    _write_log(lf, row_index=row_index, status="skipped",
                               output_files=[str(output_path)], request=row)
                    continue

                logging.info("ジョブ開始 (row=%s, refs=%d)", row_index, len(req.ref_images))

                if dry_run:
                    logging.info("Dry-run: API 呼び出しなし (row=%s)", row_index)
                    ok += 1
                    _write_log(lf, row_index=row_index, status="dry_run",
                               output_files=[str(output_path)], request=row,
                               parsed_request=asdict(req))
                    continue

                assert client is not None
                images = client.generate(req)
                written = _save_images(images, output_path)
                ok += 1
                logging.info("ジョブ完了 (row=%s, outputs=%d)", row_index, len(written))
                _write_log(lf, row_index=row_index, status="ok",
                           output_files=[str(p) for p in written], request=row,
                           parsed_request=asdict(req))
            except Exception as e:
                ng += 1
                logging.exception("ジョブ失敗 (row=%s): %s", row_index, e)
                _write_log(lf, row_index=row_index, status="error", error=str(e), request=row)

    logging.info("バッチ完了: ok=%s ng=%s log=%s", ok, ng, log_path)
    return 0 if ng == 0 else 2


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="batch_imagen",
        description="CSV から Gemini 画像生成ジョブをバッチ実行する。",
    )
    p.add_argument("--csv", type=Path, help="CSV ファイルパス（省略時はダイアログで選択）")
    p.add_argument("--limit", type=int, default=None, help="先頭 N 行のみ処理")
    p.add_argument("--dry-run", action="store_true", help="API を呼ばずパースのみ確認")
    p.add_argument("--skip-existing", action="store_true", help="出力が既存ならスキップ")
    p.add_argument("--model", default=None, help="モデル名")
    return p


def _pick_csv_dialog(initial_dir: Path | None = None) -> Path | None:
    """Windows 向け: ファイルダイアログで CSV を選択。"""
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return None
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        p = filedialog.askopenfilename(
            title="CSV ファイルを選択",
            initialdir=str(initial_dir) if initial_dir else None,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
    finally:
        root.destroy()
    return Path(p) if p else None


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    args = _build_parser().parse_args()

    csv_path = args.csv
    if not csv_path:
        csv_path = _pick_csv_dialog(initial_dir=Path.cwd())
        if not csv_path:
            _build_parser().print_help()
            return 0

    return run_batch(
        csv_path=csv_path,
        model_name=args.model,
        dry_run=args.dry_run,
        limit=args.limit,
        skip_existing=args.skip_existing,
    )


if __name__ == "__main__":
    code = main()
    if sys.gettrace() is None:
        raise SystemExit(code)
