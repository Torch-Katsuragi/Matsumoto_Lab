import json
from typing import Generator, List

import openai


import logging

try:
    # ルートからimport
    from conf import *
except:
    import os

    from dotenv import load_dotenv

    load_dotenv()

    OPENAI_APIKEY = os.environ.get("OPENAI_API_KEY")

    


class GPTHandler:
    """
    ChatGPTを使用して会話を行うためのクラス。
    """

    def __init__(self) -> None:
        """クラスの初期化メソッド。
        """
        self.last_char = ["、", "。", "！", "!", "?", "？", "\n", "}"]
        self.openai_model_name = [
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4o-2024-05-13",
            "gpt-4-turbo",
            "gpt-4-turbo-2024-04-09",
            "gpt-4-0125-preview",
            "gpt-4-turbo-preview",
            "gpt-4-1106-preview",
            "gpt-4",
            "gpt-4-0613",
            "gpt-4-32k",
            "gpt-4-32k-0613",
            "gpt-3.5-turbo-0125",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-1106",
            "gpt-3.5-turbo-instruct",
            "gpt-3.5-turbo-16k",
            "gpt-3.5-turbo-0613",
            "gpt-3.5-turbo-16k-0613",
        ]
        self.openai_vision_model_name = [
            "gpt-4-turbo",
            "gpt-4-turbo-2024-04-09",
            "gpt-4-vision-preview",
            "gpt-4-1106-vision-preview",
        ]
        self.interrupt_flg=False

    def chat_gpt(
        self,
        messages: list,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
    ) -> Generator[str, None, None]:
        """ChatGPTを使用して会話を行う

        Args:
            messages (list): 会話のメッセージ
            model (str): 使用するモデル名 (デフォルト: "gpt-4o-mini")
            temperature (float): ChatGPTのtemperatureパラメータ (デフォルト: 0.7)
        Returns:
            Generator[str, None, None]): 会話の返答を順次生成する

        """
        result = None
        if model in self.openai_vision_model_name:
            result = openai.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=1024,
                n=1,
                stream=True,
                temperature=temperature,
            )
        elif model in self.openai_model_name:
            result = openai.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=1024,
                n=1,
                stream=True,
                temperature=temperature,
                stop=None,
            )
        # 完全なレスポンスを格納する変数
        full_response = ""
        # リアルタイムでのレスポンスを格納する変数
        real_time_response = ""
        for chunk in result:
            # チャンクからテキストを取得
            text = chunk.choices[0].delta.content
            if text is None:
                pass
            else:
                # 完全なレスポンスとリアルタイムレスポンスにテキストを追加
                full_response += text
                real_time_response += text

                # リアルタイムレスポンスを1文字ずつ確認
                for index, char in enumerate(real_time_response):
                    if char in self.last_char:
                        # 区切り文字が見つかった位置
                        pos = index + 1
                        # 1文の区切りを取得
                        sentence = real_time_response[:pos]
                        # 残りの部分を更新
                        real_time_response = real_time_response[pos:]
                        # 1文完成ごとにテキストを読み上げる(遅延時間短縮のため)
                        logging.debug(f"Yielding sentence: {sentence}")
                        yield sentence
                        break
                    else:
                        pass
        # 最後に残ったリアルタイムレスポンスを返す
        logging.debug(f"Yielding final real_time_response: {real_time_response}")

        yield real_time_response

    def chat(
        self,
        messages: list,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
    ) -> Generator[str, None, None]:
        """指定したモデルを使用して会話を行う

        Args:
            messages (list): 会話のメッセージリスト
            model (str): 使用するモデル名 (デフォルト: "gpt-4o-mini")
            temperature (float): サンプリングの温度パラメータ (デフォルト: 0.7)
        Returns:
            Generator[str, None, None]): 会話の返答を順次生成する

        """
        if model in self.openai_model_name or model in self.openai_vision_model_name:
            yield from self.chat_gpt(
                messages=messages, model=model, temperature=temperature
            )
        else:
            print(f"Model name {model} can't use for this function")
            return

class JsonGPTHandler(GPTHandler):
    """
    JSON形式でChatGPTの応答を処理するためのハンドラークラス。

    GPTHandlerクラスを継承し、chatgptとのやり取り部分を親クラスから書き換えて
    streamingを1文字ずつ→json形式で1データずつに変更
    """
    def chat_gpt(
        self,
        messages: list,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
    ) -> Generator[str, None, None]:
        """ChatGPTを使用して会話を行う

        Args:
            messages (list): 会話のメッセージ
            model (str): 使用するモデル名 (デフォルト: "gpt-4o-mini")
            temperature (float): ChatGPTのtemperatureパラメータ (デフォルト: 0.7)
        Returns:
            Generator[str, None, None]): 会話の返答を順次生成する

        """
        result = None
        if model in self.openai_vision_model_name:
            result = openai.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=1024,
                n=1,
                stream=True,
                temperature=temperature,
            )
        elif model in self.openai_model_name:
            client = openai.OpenAI(api_key=OPENAI_APIKEY)
            result = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=1024,
                n=1,
                stream=True,
                temperature=temperature,
                stop=None,
                response_format={"type": "json_object"},
            )
        # 完全なレスポンスを格納する変数
        full_response = ""
        # リアルタイムでのレスポンスを格納する変数
        real_time_response = ""
        for chunk in result: # ストリーミングレスポンスを処理
            # チャンクからテキストを取得
            text = chunk.choices[0].delta.content
            if text is None:
                pass
            else:
                # 完全なレスポンスにテキストを追加
                full_response += text

                # 区切り文字があったら
                if "," in text:
                    # 区切り文字でテキストを区切る
                    fragments = text.split(",")
                    for fragment in fragments:
                        real_time_response += fragment
                        try:
                            # real_time_responseの末尾に"}"を加える
                            potential_json = real_time_response + "}"
                            # 辞書として成立するか確認(成立したら、検出されたコンマはjsonのルート要素を区切るものである)
                            parsed_dict = json.loads(potential_json)
                            # 検出されたルート要素をreal_time_responseから削除
                            real_time_response="{"
                            # 成立するならその辞書をyield
                            logging.debug(f"Yielding dictionary: {parsed_dict}")
                            yield parsed_dict
                        except json.JSONDecodeError:
                            # 辞書として成立しないばあい
                            # 人違いでしたー
                            if fragment != fragments[-1]:
                                real_time_response +=","
                else:
                    real_time_response+=text
                    continue

        # 最後に残ったリアルタイムレスポンスを返す
        try:
            parsed_dict = json.loads(real_time_response)
            # 成立するならその辞書をyield
            logging.debug(f"Yielding dictionary: {parsed_dict}")
            yield parsed_dict
        except json.JSONDecodeError:
            # 辞書として成立しないばあい
            logging.debug(f"Last element is broken!")

def test_chat_gpt_streaming():
    handler = GPTHandler()
    messages = [{"role": "user", "content": "おとぎ話の桃太郎を、あなたが覚えている限り詳細に解説してください。"}]
    model = "gpt-4o-mini"
    temperature = 0.7


    response = handler.chat(messages, model, temperature)
    
    print("".join(response))

    print()  # Ensure the output ends with a newline

def test_chat_gpt_json_streaming():
    handler = JsonGPTHandler()
    messages = [{"role": "user", "content": "おとぎ話の桃太郎を、あなたが覚えている限り詳細に解説してください。解答は起承転結ごとにjsonで出力してください"}]
    model = "gpt-4o-mini"
    temperature = 0.7

    # # 大量にリクエストしまくると、4つくらいで止まることがある。万全を期すなら、どうにかして接続をkillする必要あり？
    # n=20
    # for i in range(n):
    #     response = handler.chat(messages, model, temperature)
    #     for item in response:
    #         for key, value in item.items():
    #             print(f"{key}: {value}")
    #         #試しに最初のレスポンスが来た段階でループ脱出しまくってみる
    #         break
    
    response = handler.chat(messages, model, temperature)
    for item in response: # ここで帰ってくるのはストリーミングレスポンスなので、返答が返ってくるたびにresponseの中身が増える感じ。
        for key, value in item.items():
            print(f"{key}: {value}")

    print()  # Ensure the output ends with a newline


def main():
    logging.basicConfig(level=logging.DEBUG)
    test_chat_gpt_streaming()
    # test_chat_gpt_json_streaming()
    


if __name__ == '__main__':
    main()
