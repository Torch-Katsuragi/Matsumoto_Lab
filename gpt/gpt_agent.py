
try:
    # ルートからimport
    from gpt.gpt_handler import GPTHandler, JsonGPTHandler
    from speech.voicevox import TextToVoiceVoxWeb
    from speech.mouse_and_ear import Speaker
except ImportError:
    from .gpt_handler import GPTHandler, JsonGPTHandler
    from .speech.voicevox import TextToVoiceVoxWeb
    from .speech.mouse_and_ear import Speaker

import logging
import threading
import queue
import time

class GPTAgent:
    """
    会話AIとして最低限の個性を維持するためのクラス
    """
    def __init__(self, name="アイ", profile=None, speaker=None):
        """
        parameters
            name: name of agent
            mode_wizavo: mode of wizardvoice. "ftn" or "myt" can be chosen
            chat_limit: max size of message. if over the limit, the old message is deleted.
        """
        self.name = name
        self.profile = profile
        self.speaker = speaker
        self.recent_response = ""
        self.chatting_thread = None
        self.dialog = []
        self.is_speaking = False
        self.interrupt_event = threading.Event()  # 中断イベントを初期化
        self.end_event = threading.Event()  # チャット終了イベントを初期化
        self.response_queue = queue.Queue()  # gpt出力を保存するキューを初期化

        self.init_GPT()

    def init_GPT(self):
        # chatGPT関連設定
        self.model = "gpt-4o"
        self.gpt_handler = JsonGPTHandler()

        self.instruction = f"""
# Instruction
あなたは、会話AIです。後述するプロフィールに従い、楽しくおしゃべりしてください。
ただし、以下の点に気を付けてください
- 一度に話す内容は一文にとどめる
- 返答は短かくして相手に話させるのが望ましい
- userの話に共感する
- 会話を続ける努力をする
- userの事は「user」とは呼ばない。名前を教えられたら名前で呼ぶ
"""
        if self.profile is None:
            self.profile = f"""
# Profile
あなたのプロフィールは以下の通りです：
- 名前は{self.name}
- 猫耳メイドの女の子
- 祖先に猫の妖怪がいて、猫耳と尻尾は自前の物
- 猫っぽいしゃべり方
- userとは友達。敬語も使わない
- 趣味は料理とガーデニング。特にハーブを育てるのが好き
- 好きな食べ物は魚料理。特にサーモンのグリルが大好物
- 休日はよくカフェ巡りをして、新しいスイーツを試すのが楽しみ
- 少しおっちょこちょいなところがあり、よくドジを踏む
- userのことをとても大切に思っており、いつも元気づけようとする
- 音楽が好きで、特にクラシックとジャズをよく聴く
- 夜は星を眺めるのが好きで、星座に詳しい
"""
        self.output_format = r"""
# Output format
出力はJSON形式で、以下のフォーマットに従ってください。
{{"response": "ここに、あなたのuserへの言葉を入れる", "emotion": "ここに、あなたの今の感情を入れる"}}
"""
        personality = self.instruction + self.profile + self.output_format
        logging.debug("キャラ設定\n" + personality)
        self.personality_message = [{'role': 'system', 'content': personality}]

    def get_name(self):
        return self.name

    def get_exception_response(self):
        """
        GPTの応答の取得に失敗した時に返す応答を記載 (各エージェント独自のものを使いたい)
        こういうとこユニークにするとかわいげがあるよね(主観)
        """
        return ""

    def chat(self, message: str):
        """
        userの言葉に対するchatGPTの応答を取得
        """
        self.dialog.append({'role': 'user', 'content': message})
        messages = self.personality_message + self.dialog
        self.response = self.gpt_handler.chat(messages, self.model)  # ストリーミングしている以上、ここから帰ってくるのはストリーミングレスポンスだ
        return self.response

    def pop_response(self):
        if self.dialog[-1]['role'] == 'user':
            self.dialog.append({'role': 'assistant', 'content': ""})
        full_response = {}
        self.is_speaking = True
        for item in self.response:
            full_response.update(item)
            self.dialog[-1] = {'role': 'assistant', 'content': str(full_response)}
            yield item
        logging.debug("gpt responding ended")
        self.is_speaking = False

    def speak(self, text):
        """
        入力されたテキスト(もしくは最後のGPTの応答)を音声合成して出力。
        一応エージェントからも音声を出力できるようにしておいた
        """
        if self.speaker is not None:
            self.speaker.speak(text)
        print(text)

    def interrupt_speaking(self):
        """
        会話中に言葉を遮られたらいったん話すのをやめる
        """
        self.speaker.interrupt()
        if self.is_speaking:
            self.is_speaking = False
            while self.dialog and self.dialog[-1]['role'] != 'user':
                self.dialog.pop()
            self.dialog.pop()

    def update_dialog(self):
        """
        self.response_queueの要素をself.dialogに追加する
        """
        full_response = {}
        while not self.response_queue.empty():
            response_item = self.response_queue.get()
            full_response.update(response_item)
        logging.debug("dialog updated")
        self.dialog.append({'role': 'assistant', 'content': str(full_response)})

    def start_chatting(self, message: str):
        """
        userの言葉に対するchatGPTの応答を取得
        """
        self.update_dialog()
        self.dialog.append({'role': 'user', 'content': message})

        gpt_handler = JsonGPTHandler()
        messages = self.personality_message + self.dialog
        self.chatting_thread = threading.Thread(target=GPTAgent.chatting_loop, name="chatter", args=(self.speaker, self.model, messages, self.response_queue, gpt_handler, self.interrupt_event, self.end_event))
        self.chatting_thread.start()

    @staticmethod
    def chatting_loop(speaker: Speaker, model, messages, queue, handler, stop_event, end_event):
        start_time = time.time()
        response = handler.chat(messages, model)  # ストリーミングしている以上、ここから帰ってくるのはストリーミングレスポンスだ
        for item in response:
            if stop_event.is_set():
                speaker.interrupt()
                return
            queue.put(item)
            if "response" in item:
                speaker.speak(item["response"])
        end_event.set()
        response_time = time.time() - start_time
        logging.debug(f"応答時間: {response_time}秒")

    def stop_chatting(self):
        if self.chatting_thread and self.chatting_thread.is_alive():
            self.interrupt_event.set()  # スレッド終了イベントをセット
            self.chatting_thread = None  # スレッドオブジェクトをクリアして次に進む。まだスレッドは動いてるけど、フラグ送ったしそのうち終了してくれるよ。

    def cancel_chatting(self):
        """前の話とその続きが同時に来るときは、userの発話までさかのぼってself.dialogをリセット"""
        # 最後の'user'の発話のインデックスを探す
        last_user_index = next((i for i in range(len(self.dialog) - 1, -1, -1) if self.dialog[i]['role'] == 'user'), None)

        # 'user'の発話が見つかった場合、その発話までself.dialogをリセットする
        if last_user_index is not None:
            self.dialog = self.dialog[:last_user_index]
