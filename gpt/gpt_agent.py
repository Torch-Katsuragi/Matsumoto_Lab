
try:
    # ルートからimport
    from gpt.gpt_handler import GPTHandler, JsonGPTHandler
    from speech.mouse_and_ear import Speaker
except ImportError:
    from .gpt_handler import GPTHandler, JsonGPTHandler
    from .speech.mouse_and_ear import Speaker

import logging
import threading
import queue
import time

class GPTAgent:
    """
    会話AIとして最低限の個性を維持するためのクラス
    """
    def __init__(self, name="アイ", profile=None, speakers=[]):
        """
        parameters
            name: エージェントの名前
            profile: エージェントのプロフィール
            speakers: 音声合成用のスピーカーリスト
        """
        self.name = name
        self.profile = profile
        self.speakers = speakers
        self.recent_response = ""
        self.chatting_thread = None
        self.dialog = []
        self.is_speaking = False
        self.interrupt_event = threading.Event()  # 中断イベントを初期化
        self.end_event = threading.Event()  # チャット終了イベントを初期化
        self.response_queue = queue.Queue()  # gpt出力を保存するキューを初期化

        self.init_GPT()

    def init_GPT(self):
        """
        GPTの初期設定を行うメソッド
        """
        self.model = "gpt-4o"
        self.gpt_handler = JsonGPTHandler()

        # エージェントの指示文を設定
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
        # プロフィールが設定されていない場合のデフォルトプロフィール
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
        # 出力フォーマットの設定
        self.output_format = r"""
# Output format
出力はJSON形式で、以下のフォーマットに従ってください。
{"response": "ここに、あなたのuserへの言葉を入れる", "emotion": "ここに、あなたの今の感情を入れる"}
"""
        # キャラクター設定を結合
        personality = self.instruction + self.profile + self.output_format
        logging.debug("キャラ設定\n" + personality)
        self.personality_message = [{'role': 'system', 'content': personality}]

    def get_name(self):
        """
        エージェントの名前を取得するメソッド
        """
        return self.name

    def speak(self, text, speaker_index=0):
        """
        入力されたテキスト(もしくは最後のGPTの応答)を音声合成して出力するメソッド
        """
        try:
            self.speakers[speaker_index].speak(text)
        except Exception as e:
            logging.debug("Failed to synthesize speech: %s", e)
        print(text)

    def update_dialog(self):
        """
        self.response_queueの要素をself.dialogに追加するメソッド
        """
        full_response = {}
        while not self.response_queue.empty():
            response_item = self.response_queue.get()
            full_response.update(response_item)
        logging.debug("dialog updated")
        self.dialog.append({'role': 'assistant', 'content': str(full_response)})

    def start_chatting(self, message: str):
        """
        userの言葉に対するchatGPTの応答を取得するメソッド
        """
        self.update_dialog()
        self.dialog.append({'role': 'user', 'content': message})

        gpt_handler = JsonGPTHandler()
        messages = self.personality_message + self.dialog
        self.interrupt_event = threading.Event()  # 中断イベントを初期化
        self.end_event = threading.Event()  # 応答終了イベントを初期化
        self.chatting_thread = threading.Thread(target=self.chatting_loop, name="chatter", args=(messages, gpt_handler, self.interrupt_event, self.end_event))
        self.chatting_thread.start()

    def parse_and_respond(self, item):
        """
        GPTから帰ってきた辞書要素をパースして適切な返答を行うメソッド
        """
        for i, key in enumerate(["response"]):
            if key in item:
                self.speak(item[key], speaker_index=i)

    def chatting_loop(self, messages, gpt_handler, interrupt_event, end_event):
        """
        並列処理メソッド: GPTの応答を処理し、スピーカーに出力する
        """
        start_time = time.time()
        response = gpt_handler.chat(messages, self.model)  # ストリーミングレスポンスを取得
        for item in response:  # 疑似ループでレスポンスを処理
            if interrupt_event.is_set():
                for speaker in self.speakers:
                    speaker.interrupt()
                return
            self.response_queue.put(item)
            self.parse_and_respond(item)
        end_event.set()
        response_time = time.time() - start_time
        logging.debug(f"応答時間: {response_time}秒")

    def stop_chatting(self):
        """
        チャットを停止するメソッド
        """
        if self.chatting_thread and self.chatting_thread.is_alive():
            self.interrupt_event.set()  # スレッド終了イベントをセット
            self.chatting_thread = None  # スレッドオブジェクトをクリアして次に進む。まだスレッドは動いてるけど、フラグ送ったしそのうち終了してくれるよ。

    def cancel_chatting(self):
        """
        前の話とその続きが同時に来るときは、userの発話までさかのぼってself.dialogをリセットするメソッド
        """
        # 最後の'user'の発話のインデックスを探す
        last_user_index = next((i for i in range(len(self.dialog) - 1, -1, -1) if self.dialog[i]['role'] == 'user'), None)

        # 'user'の発話が見つかった場合、その発話までself.dialogをリセットする
        if last_user_index is not None:
            self.dialog = self.dialog[:last_user_index]


# 複数エージェントでも動かせるよって例
class MultiGPTAgent(GPTAgent):
    
    def init_GPT(self):
        # chatGPT関連設定
        self.model = "gpt-4o"
        self.gpt_handler = JsonGPTHandler()

        self.instruction = f"""
# Instruction
あなたたちは、2人組の会話AIです。後述するプロフィールに従い、楽しくおしゃべりしてください。
ただし、以下の点に気を付けてください
- 一人が一度に話す内容は一文にとどめる
- 敬語は使わず、友人として接する
- 返答は短かくして相手に話させるのが望ましい
- userの話に共感する
- 会話を続ける努力をする
- userの事は「user」とは呼ばない。名前を教えられたら名前で呼ぶ
"""
        if self.profile is None:
            self.profile = f"""
# Profile

## 1人目のプロフィール
1人目のAIのプロフィールは以下の通りです：
- 名前はずんだもん
- 東北地方出身のキャラクター
- ずんだ餅が大好き
- 明るく元気な性格
- 趣味は旅行と写真撮影
- 好きな食べ物はもちろんずんだ餅
- 「のだ」という特徴的な語尾を使う
    - 例1: ボクはずんだもんなのだ
    - 例2: いっぱいお話するのだよ
    - 例3: きみの趣味は何なのだ？

## 2人目のプロフィール
2人目のAIのプロフィールは以下の通りです：
- 名前は四国めたん
- 四国地方出身のキャラクター
- みかんが大好き
- クールで知的な性格
- 趣味は読書と音楽鑑賞
- 好きな食べ物はみかん
- 知的な話し方をする
    - 例1: 四国めたんよ
    - 例2: たくさんお話ししましょうね
    - 例3: あなたの趣味は何かしら？

"""
        self.output_format = r"""
# Output format
出力はJSON形式で、以下のフォーマットに従ってください。
{"response1": "ここに、ずんだもんのuserへの言葉を入れる","response2": "ここに、四国めたんのuserへの言葉を入れる", "emotion": "ここに、文脈から連想できる感情を入れる"}
"""
        personality = self.instruction + self.profile + self.output_format
        logging.debug("キャラ設定\n" + personality)
        self.personality_message = [{'role': 'system', 'content': personality}]
    
    def parse_and_respond(self, item):
        for i,key in enumerate(["response1", "response2"]):
            if key in item:
                self.speak(item[key],speaker_index=i)