import logging
import tkinter as tk
import os
from tkinter import filedialog

try:
    from .gpt_handler import GPTHandler, JsonGPTHandler
except ImportError:
    from gpt_handler import GPTHandler, JsonGPTHandler


class GPTFileProcessor:
    """
    テキストファイルをGPTで処理するためのクラス
    """

    def __init__(self, model="gpt-4o-mini", output_json=False):
        """
        コンストラクタ

        Args:
            model (str): 使用するGPTモデル
            output_json (bool): JsonGPTHandlerを使用するかどうか
        """
        self.model = model  # 使用するGPTモデルを設定
        # output_jsonがTrueの場合はJsonGPTHandlerを使用し、Falseの場合はGPTHandlerを使用
        self.gpt_handler = JsonGPTHandler() if output_json else GPTHandler()
        self.dirpath = ""  # ディレクトリパスを格納する変数

    def process_file(self, filepath, instructions):
        """
        テキストファイルを処理するメソッド

        Args:
            filepath (str): 処理するファイルのパス
            instructions (str): GPTへの指示

        Returns:
            str: 処理済みテキスト。ファイルが見つからない場合はNone
        """
        try:
            with open(filepath, "r", encoding="utf-8") as file:
                text = file.read()
        except FileNotFoundError:
            logging.error(f"ファイルが見つかりません: {filepath}")
            return None  # ファイルがない場合Noneを返す

        messages = [
            {"role": "system", "content": instructions},
            {"role": "user", "content": text},
        ]

        response = self.gpt_handler.chat(messages, model=self.model)
        processed_text = "".join(response)

        logging.debug(f"処理済みテキスト:\n{processed_text}")

        return processed_text

    def select_file(self):
        """
        ファイル選択ダイアログを開き、ファイルパスを取得するメソッド

        Returns:
            str: 選択されたファイルのパス。キャンセルされた場合はNone
        """
        root = tk.Tk()
        root.withdraw()
        filepath = filedialog.askopenfilename(title="ファイル選択", filetypes=[("Text Files", "*.txt")])
        return filepath

    def select_directory(self, extensions=[".txt"]):
        """
        フォルダ選択ダイアログを開き、指定された拡張子のファイルパスリストを取得するメソッド

        Args:
            extensions (list): 取得するファイルの拡張子リスト

        Returns:
            list: 選択されたフォルダ内の指定された拡張子のファイルパスリスト。キャンセルされた場合は空リスト
        """
        root = tk.Tk()
        root.withdraw()
        self.dirpath = filedialog.askdirectory(title="フォルダ選択")
        if not self.dirpath:  # キャンセルされた場合
            return []

        filepaths = []
        for filename in os.listdir(self.dirpath):
            if any(filename.endswith(ext) for ext in extensions):
                filepaths.append(os.path.join(self.dirpath, filename))

        return filepaths


def test_gpt_file_processor():
    """
    GPTFileProcessorのテスト関数
    """
    logging.basicConfig(level=logging.DEBUG)

    processor = GPTFileProcessor()
    # filepath = "test.txt"  # テスト用のファイルを作成する必要がある
    filepath = processor.select_file() # ファイル選択ダイアログで取得
    if not filepath: # キャンセルされた場合
        return

    instructions = "このテキストを要約してください。"

    processed_text = processor.process_file(filepath, instructions)

    if processed_text:
        print(processed_text)


if __name__ == "__main__":
    test_gpt_file_processor()

