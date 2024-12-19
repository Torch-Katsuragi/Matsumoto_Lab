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

    def __init__(self, model="gpt-4o-mini"):
        """
        コンストラクタ

        Args:
            model (str): 使用するGPTモデル
            output_json (bool): JsonGPTHandlerを使用するかどうか
        """
        self.model = model  # 使用するGPTモデルを設定
        self.gpt_handler = JsonGPTHandler()

    def process_file(self, instructions, output_field={"main_output":"タスクの結果"}, filepath:str=""):
        """
        テキストファイルを処理するメソッド

        Args:
            filepath (str): 処理するファイルのパス
            instructions (str): GPTへの指示

        Returns:
            str: 処理済みテキスト。ファイルが見つからない場合はNone
        """
        # filepathが空の場合，select_fileから見つけてくる
        if not filepath:
            filepath = self.select_file()
            if not filepath:  # キャンセルされた場合
                return None
        try:
            with open(filepath, "r", encoding="utf-8") as file:
                text = file.read()
        except FileNotFoundError:
            logging.error(f"ファイルが見つかりません: {filepath}")
            return None  # ファイルがない場合Noneを返す
        
        output_format=f"""

出力はJSON形式とし，以下のような形式にすること．ただし，埋められない項目がある場合は"unknown"とすること
{output_field}
"""
        messages = [
            {"role": "system", "content": instructions+output_format},
            {"role": "user", "content": text},
        ]

        streaming_object = self.gpt_handler.chat(messages, model=self.model)

        # 無駄にstreamingしているので，全部出てくるまで待つ
        response={}
        for item in streaming_object:  # 疑似ループでレスポンスを処理
            response.update(item)  # 応答アイテムをresponseに追加

        logging.debug(f"処理済みテキスト:\n{response}")

        return response
    
    def process_on_directory(self, instructions, output_field={"main_output":"タスクの結果"}, dirpath:str="", extensions:list=[".txt"], output_path=""):
        """
        特定のディレクトリにあるフォルダすべてに対してprocess_fileを実行するメソッド
        """
        # フォルダ選択ダイアログを開き、フォルダパスを取得 -> dirpath
        if not dirpath:
            dirpath = self.select_directory()
            if not dirpath:  # キャンセルされた場合
                return
        
        # dirpathからフォルダ内の指定のextのファイルパスをすべて取得 -> filepaths
        filepaths = []
        for filename in os.listdir(dirpath):
            if any(filename.endswith(ext) for ext in extensions):
                filepaths.append(os.path.join(dirpath, filename))
        
        # filepathsの要素それぞれに対してprocess_fileを実行し，表として保存 -> output_table
        output_table = []
        # output_tableの最初の行に項目名を追加
        header = ["file_name"] + list(output_field.keys())
        output_table.append(header)
        # ファイルごとにAI処理して表に保存
        for filepath in filepaths:
            processed_data = self.process_file(instructions, output_field=output_field, filepath=filepath)
            if processed_data is not None:
                # 各ファイルの結果を表形式で保存
                row = [os.path.basename(filepath)] + [processed_data.get(key, "") for key in header[1:]]
                output_table.append(row)
        
        self.save_output_table(output_table,dirpath)

        return output_table
    
    def save_output_table(self, data, dirpath, filepath="output.csv"):
        """
        出力結果を指定されたパスにCSV形式で保存するメソッド

        Args:
            data (list): 保存するデータ（リスト形式）
            output_path (str): 保存先のファイルパス。デフォルトは"output.csv"
        """
        import csv

        try:
            full_path = os.path.join(dirpath, filepath)  # dirpathとfilepathを結合してフルパスを作成
            with open(full_path, 'w', newline='', encoding='shift-jis') as f:
                writer = csv.writer(f)
                writer.writerows(data)
            logging.info(f"出力結果を{full_path}に保存しました。")
        except Exception as e:
            logging.error(f"出力結果の保存中にエラーが発生しました: {e}")


    def select_file(self):
        """
        ファイル選択ダイアログを開き、ファイルパスを取得するメソッド

        Returns:
            str: 選択されたファイルのパス。キャンセルされた場合はNone
        """
        root = tk.Tk()
        root.withdraw()
        filepath = filedialog.askopenfilename(title="ファイル選択")
        return filepath

    def select_directory(self):
        """
        フォルダ選択ダイアログを開き、指定された拡張子のファイルパスリストを取得するメソッド

        Args:
            extensions (list): 取得するファイルの拡張子リスト

        Returns:
            list: 選択されたフォルダ内の指定された拡張子のファイルパスリスト。キャンセルされた場合は空リスト
        """
        root = tk.Tk()
        root.withdraw()
        dirpath = filedialog.askdirectory(title="フォルダ選択")
        if not dirpath:  # キャンセルされた場合
            return []
        return dirpath





def test_gpt_file_processor():
    """
    GPTFileProcessorのテスト関数
    """
    logging.basicConfig(level=logging.DEBUG)

    processor = GPTFileProcessor()


    instructions = "このテキストを要約してください。"

    processed_text = processor.process_file(instructions)

    if processed_text:
        print(processed_text)


def test_process_on_directory():
    """
    process_on_directoryメソッドのテスト関数
    """
    logging.basicConfig(level=logging.DEBUG)

    processor = GPTFileProcessor()

    instructions = "このテキストファイルは，会話の様子を録音したものです．要約してください。"

    output_field={"title":"ファイルの内容を一言で要約","topics":"主要なトピック (半角スペースで区切る)","main_output":"タスクの結果","date":"年月日から時刻まで (ex. 2024.12.18 16:15)","total time":"タイムスタンプから見る会話時間の合計"}

    processed_texts = processor.process_on_directory(instructions,output_field)

    for processed_text in processed_texts:
        if processed_text:
            print(processed_text)


if __name__ == "__main__":
    # test_gpt_file_processor()
    test_process_on_directory()

