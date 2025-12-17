"""
CSV から Gemini 画像生成ジョブをまとめて実行する。

gemini-3-pro-image-preview を使用し、マルチモーダル入力で参照画像（最大14枚）を渡せる。

CSV 仕様:
- output_dir: 任意。出力先フォルダ（絶対パス）。省略時は Downloads/generated_image/<timestamp>。
- output_filename: 任意。出力ファイル名（拡張子なし）。
- prompt: 必須。画像生成指示（日本語OK）。{0}, {1}, ... で参照画像を挿入可能。
- ref_images: 任意。参照画像のパス（セミコロン区切りで最大14枚）。
- aspect_ratio: 任意。アスペクト比（1:1, 16:9, 9:16, 4:3, 3:4）。デフォルト 1:1。
- resolution: 任意。出力解像度（1K, 2K, 4K）。デフォルト 1K。
- number_of_images: 任意。生成枚数（デフォルト1）。
- seed: 任意（将来用）。
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

if __package__ in (None, ""):
    # `python image/batch_imagen3.py` で実行された場合、sys.path[0] が image/ になり
    # `import image...` が失敗するので、リポジトリルートを追加する。
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    # package として実行: python -m image.batch_imagen
    from .conf import GCP_LOCATION, GCP_PROJECT_ID, IMAGEN3_MODEL
    from .imagen_client import ImagenClient, ImagenRequest
except ImportError:
    # スクリプト直叩き: python image/batch_imagen.py
    from image.conf import GCP_LOCATION, GCP_PROJECT_ID, IMAGEN3_MODEL
    from image.imagen_client import ImagenClient, ImagenRequest


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _timestamp_compact_local() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _downloads_dir() -> Path:
    """
    出力は Downloads 固定。
    Windows 前提で Path.home()/Downloads を基本にする。
    """

    p = Path.home() / "Downloads"
    return p if p.exists() else Path.home()


def _run_output_dir() -> Path:
    # generated_image\<YYYYMMDD_HHMMSS>
    return _downloads_dir() / "generated_image" / _timestamp_compact_local()


_WINDOWS_INVALID_CHARS = set(r'\/:*?"<>|')


def _sanitize_basename(s: str) -> str:
    # パスセパレータ/禁止文字を潰す（置換）
    out = []
    for ch in s:
        if ch in _WINDOWS_INVALID_CHARS or ord(ch) < 32:
            out.append("_")
        else:
            out.append(ch)
    name = "".join(out).strip().strip(".")
    return name or "image"


def _t2i_basename_from_prompt(prompt: str, *, max_len: int = 20) -> str:
    """
    ルール:
    - ファイル名に使えない文字が登場するか、max_len に達するまで prompt を抜き出す
    """

    buf: List[str] = []
    for ch in prompt.strip():
        if ch in _WINDOWS_INVALID_CHARS or ord(ch) < 32:
            break
        buf.append("_" if ch.isspace() else ch)
        if len(buf) >= max_len:
            break
    return _sanitize_basename("".join(buf))


def _unique_path(dir_path: Path, base: str, *, row_index: int, used: Set[str]) -> Path:
    """
    衝突回避（同名promptや同名入力画像が来る可能性があるため）。
    ルールは維持しつつ、衝突時のみ row_index を付与する。
    """

    base = _sanitize_basename(base)
    candidate = base
    if candidate in used or (dir_path / f"{candidate}.png").exists():
        candidate = f"{base}_{row_index:05d}"
    used.add(candidate)
    return dir_path / f"{candidate}.png"


def _to_int(x: str | None) -> int | None:
    if x is None:
        return None
    s = str(x).strip()
    if not s:
        return None
    return int(s)


def _to_str(x: str | None) -> str | None:
    if x is None:
        return None
    s = str(x).strip()
    return s or None


def _to_path(x: str | None) -> Path | None:
    s = _to_str(x)
    if not s:
        return None
    # 環境変数展開だけは効かせる（Windowsでも役立つ）
    expanded = os.path.expandvars(s)
    return Path(expanded)


def _resolve_input_path(p: Path | None, base_dir: Path) -> Path | None:
    if p is None:
        return None
    if p.is_absolute():
        return p
    return (base_dir / p).resolve()


def _save_images(image_bytes_list: List[bytes], output_path: Path) -> List[Path]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []

    if len(image_bytes_list) <= 1:
        output_path.write_bytes(image_bytes_list[0])
        written.append(output_path)
        return written

    stem = output_path.stem
    suffix = output_path.suffix or ".png"
    for i, b in enumerate(image_bytes_list, start=1):
        p = output_path.with_name(f"{stem}_{i:02d}{suffix}")
        p.write_bytes(b)
        written.append(p)
    return written


def _parse_ref_images(raw: str | None, base_dir: Path) -> tuple[Path, ...]:
    """ref_images 列をセミコロン区切りで解析してPathのタプルを返す。"""
    if not raw:
        return ()
    paths = []
    for part in raw.split(";"):
        p = part.strip()
        if not p:
            continue
        resolved = _resolve_input_path(_to_path(p), base_dir)
        if resolved:
            paths.append(resolved)
    return tuple(paths)


def _parse_row(
    row: Dict[str, str],
    *,
    base_dir: Path,
    validate_paths: bool = True,
) -> ImagenRequest:
    prompt = _to_str(row.get("prompt"))
    if not prompt:
        raise ValueError("Missing prompt")

    ref_images = _parse_ref_images(row.get("ref_images"), base_dir)

    req = ImagenRequest(
        prompt=prompt,
        ref_images=ref_images,
        number_of_images=_to_int(row.get("number_of_images")) or 1,
        aspect_ratio=_to_str(row.get("aspect_ratio")) or "1:1",
        resolution=_to_str(row.get("resolution")) or "1K",
        seed=_to_int(row.get("seed")),
    )

    if validate_paths:
        for ref_path in req.ref_images:
            if not ref_path.exists():
                raise FileNotFoundError(f"ref_images not found: {ref_path}")

    return req


def run_batch(
    csv_path: Path,
    *,
    project_id: str | None,
    location: str | None,
    model_name: str | None,
    dry_run: bool,
    limit: int | None,
    skip_existing: bool,
) -> int:
    csv_path = csv_path.resolve()
    base_dir = csv_path.parent

    out_dir = _run_output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "imagen_batch_log.jsonl"

    client = None if dry_run else ImagenClient(project_id=project_id, location=location, model_name=model_name)

    ok = 0
    ng = 0
    used_names: Set[str] = set()
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f, log_path.open("a", encoding="utf-8") as lf:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV has no header")

        for idx0, row in enumerate(reader):
            row_index = idx0 + 1
            if limit is not None and row_index > limit:
                break

            try:
                req = _parse_row(
                    row,
                    base_dir=base_dir,
                    validate_paths=not dry_run,
                )

                # output_dir 列があればそれを使う（絶対パス）、なければデフォルト
                explicit_out_dir = _to_str(row.get("output_dir"))
                if explicit_out_dir:
                    row_out_dir = Path(explicit_out_dir)
                    row_out_dir.mkdir(parents=True, exist_ok=True)
                else:
                    row_out_dir = out_dir

                # output_filename 列があればそれを使う、なければ自動生成
                explicit_name = _to_str(row.get("output_filename"))
                if explicit_name:
                    base_name = Path(explicit_name).stem
                elif req.ref_images:
                    base_name = req.ref_images[0].stem
                else:
                    base_name = _t2i_basename_from_prompt(req.prompt, max_len=20)

                output_path = _unique_path(row_out_dir, base_name, row_index=row_index, used=used_names)
                if skip_existing and output_path.exists():
                    logging.info("Skip existing output: %s", output_path)
                    ok += 1
                    _write_log(lf, row_index=row_index, status="skipped", output_files=[str(output_path)], request=row)
                    continue

                logging.info("Job start (row=%s refs=%d)", row_index, len(req.ref_images))

                if dry_run:
                    logging.info("Dry-run: no API call (row=%s)", row_index)
                    ok += 1
                    _write_log(
                        lf,
                        row_index=row_index,
                        status="dry_run",
                        output_files=[str(output_path)],
                        request=row,
                        parsed_request=asdict(req),
                    )
                    continue

                assert client is not None
                images = client.generate(req)
                written = _save_images(images, output_path)
                ok += 1
                logging.info("Job done (row=%s outputs=%s)", row_index, len(written))
                _write_log(
                    lf,
                    row_index=row_index,
                    status="ok",
                    output_files=[str(p) for p in written],
                    request=row,
                    parsed_request=asdict(req),
                )
            except Exception as e:
                ng += 1
                logging.exception("Job failed (row=%s): %s", row_index, e)
                _write_log(lf, row_index=row_index, status="error", error=str(e), request=row)

    logging.info("Batch finished: ok=%s ng=%s log=%s", ok, ng, log_path)
    return 0 if ng == 0 else 2


def _write_log(
    lf,
    *,
    row_index: int,
    status: str,
    output_files: List[str] | None = None,
    error: str | None = None,
    request: Dict[str, str] | None = None,
    parsed_request: Dict | None = None,
) -> None:
    payload = {
        "time": _now_iso(),
        "row_index": row_index,
        "status": status,
        "output_files": output_files or [],
        "error": error,
        "request": request or {},
        "parsed_request": parsed_request,
    }
    # Path 等が混ざっても落ちないように default=str で文字列化
    lf.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    lf.flush()


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="imagen_batch", description="Run Gemini image generation batch jobs from CSV.")
    p.add_argument("--csv", required=True, type=Path, help="Path to CSV file (utf-8).")

    p.add_argument("--limit", type=int, default=None, help="Process only first N rows.")
    p.add_argument("--dry-run", action="store_true", help="Parse CSV and log, but do not call API.")
    p.add_argument("--skip-existing", action="store_true", help="Skip rows whose output_path already exists.")

    p.add_argument("--project", default=GCP_PROJECT_ID, help="GCP project id (unused, for compatibility).")
    p.add_argument("--location", default=GCP_LOCATION, help="GCP location (unused, for compatibility).")
    p.add_argument("--model", default=IMAGEN3_MODEL, help="Model name (env IMAGEN_MODEL). Default: gemini-3-pro-image-preview.")
    return p


def _pick_csv_by_dialog(initial_dir: Path | None = None) -> Path | None:
    """
    Windows の F5 実行（引数なし）向けに、ファイルダイアログで CSV を選ばせる。
    キャンセルされたら None。
    """

    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as e:
        logging.error("Failed to import tkinter: %s", e)
        return None

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        p = filedialog.askopenfilename(
            title="Select CSV file",
            initialdir=str(initial_dir) if initial_dir else None,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
    finally:
        root.destroy()
    return Path(p) if p else None


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    parser = build_argparser()
    # 引数なしで起動された場合（IDEデバッグ等）はヘルプだけ出して正常終了にする
    if len(sys.argv) <= 1:
        # F5 実行向け: CSV をGUIで選ぶ
        csv_path = _pick_csv_by_dialog(initial_dir=Path.cwd())
        if not csv_path:
            parser.print_help()
            return 0

        code = run_batch(
            csv_path=csv_path,
            project_id=GCP_PROJECT_ID,
            location=GCP_LOCATION,
            model_name=IMAGEN3_MODEL,
            dry_run=False,
            limit=None,
            skip_existing=False,
        )
        # F5/デバッガ実行では SystemExit で止まりがちなので、ここは return にする
        return code

    args = parser.parse_args()
    code = run_batch(
        csv_path=args.csv,
        project_id=args.project,
        location=args.location,
        model_name=args.model,
        dry_run=args.dry_run,
        limit=args.limit,
        skip_existing=args.skip_existing,
    )
    return code


if __name__ == "__main__":
    exit_code = main()
    # デバッガ実行では SystemExit が例外停止しやすいので、通常実行時のみ exit code を返す
    if sys.gettrace() is None:
        raise SystemExit(exit_code)




