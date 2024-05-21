

# 相対パスからimport
from .gpt_handler import GPTHandler, JsonGPTHandler

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
        コンストラクタ

        Parameters:
            name (str): エージェントの名前
            profile (str): エージェントのプロフィール
            speakers (list): 音声合成用のスピーカーリスト
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
        self.characters=[]

        self.init_GPT()

    def init_GPT(self):
        """
        GPTの初期設定を行うメソッド
        """
        self.model = "gpt-4o"  # 使用するGPTモデルを設定
        self.gpt_handler = JsonGPTHandler()  # GPTハンドラーを初期化

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
{"アイ": "ここに、あなたのuserへの言葉を入れる", "emotion": "ここに、あなたの今の感情を入れる"}
"""
        # キャラクター設定を結合
        personality = self.instruction + self.profile + self.output_format
        self.characters=[self.name]
        logging.debug("キャラ設定\n" + personality)  # キャラクター設定をデバッグログに出力
        self.personality_message = [{'role': 'system', 'content': personality}]  # キャラクター設定をシステムメッセージとして保存

    def get_name(self):
        """
        エージェントの名前を取得するメソッド

        Returns:
            str: エージェントの名前
        """
        return self.name

    def speak(self, text, speaker_index=0):
        """
        入力されたテキスト(もしくは最後のGPTの応答)を音声合成して出力するメソッド

        Parameters:
            text (str): 音声合成するテキスト
            speaker_index (int): 使用するスピーカーのインデックス
        """
        try:
            self.speakers[speaker_index].speak(text)  # 指定されたスピーカーでテキストを音声合成
        except Exception as e:
            logging.debug("Failed to synthesize speech: %s", e)  # 音声合成に失敗した場合のエラーログ
        print(text)  # 合成された音声テキストをコンソールに出力
    

    def update_dialog(self)->bool:
        """
        self.response_queueの要素をself.dialogに追加するメソッド
        何か要素をdialogに保存したらtrue, そうでないならfalseを返す
        """
        full_response = {}  # 完全な応答を格納する辞書
        while not self.response_queue.empty():
            response_item = self.response_queue.get()  # キューから応答アイテムを取得
            full_response.update(response_item)  # 応答アイテムを完全な応答に追加
        logging.debug("dialog updated: %s", full_response)  # ダイアログが更新されたことをデバッグログに出力し、full_responseの中身も出力
        if self.dialog and self.dialog[-1]['role'] == 'assistant':
            # 最後の要素のcontentを取得
            last_content = self.dialog[-1]['content']
            # contentが辞書形式の文字列であるか確認し、辞書に変換
            last_dict = eval(last_content) if last_content.startswith('{') and last_content.endswith('}') else {}
            # full_responseを既存の辞書に追加
            last_dict.update(full_response)
            # 更新された辞書を文字列に変換してcontentに格納
            self.dialog[-1]['content'] = str(last_dict)
        else:
            # 最後の要素がassistantでない場合、新しい要素を追加
            if full_response:
                self.dialog.append({'role': 'assistant', 'content': str(full_response)})  # ダイアログにアシスタントの応答を追加
        return bool(full_response)

    def start_chatting(self, message: str):
        """
        userの言葉に対するchatGPTの応答を取得するメソッド

        Parameters:
            message (str): userのメッセージ
        """
        self.update_dialog()  # ダイアログを更新
        self.dialog.append({'role': 'user', 'content': message})  # ダイアログにユーザーのメッセージを追加

        gpt_handler = JsonGPTHandler()  # GPTハンドラーを初期化
        messages = self.personality_message + self.dialog  # メッセージリストを作成
        self.interrupt_event = threading.Event()  # 中断イベントを初期化
        self.end_event = threading.Event()  # 応答終了イベントを初期化
        # チャットスレッドを開始
        self.chatting_thread = threading.Thread(target=self.chatting_loop, name="chatter", args=(messages, gpt_handler, self.interrupt_event, self.end_event))
        self.chatting_thread.start()

    def parse_and_respond(self, item):
        """
        GPTから帰ってきた辞書要素をパースして適切な返答を行うメソッド

        Parameters:
            item (dict): GPTからの応答
        """
        
        for i, key in enumerate(self.characters):
            if key in item:
                self.speak(item[key], speaker_index=i)  # 応答を音声合成して出力

    def chatting_loop(self, messages, gpt_handler, interrupt_event, end_event):
        """
        並列処理メソッド: GPTの応答を処理し、スピーカーに出力する

        Parameters:
            messages (list): GPTに送信するメッセージのリスト
            gpt_handler (JsonGPTHandler): GPTハンドラー
            interrupt_event (threading.Event): 中断イベント
            end_event (threading.Event): 応答終了イベント
        """
        start_time = time.time()  # 処理開始時間を記録
        response = gpt_handler.chat(messages, self.model)  # ストリーミングレスポンスを取得
        for item in response:  # 疑似ループでレスポンスを処理
            if interrupt_event.is_set():  # 中断イベントがセットされているか確認
                return
            self.response_queue.put(item)  # 応答アイテムをキューに追加
            self.parse_and_respond(item)  # 応答アイテムをパースして返答
        end_event.set()  # 応答終了イベントをセット
        response_time = time.time() - start_time  # 応答時間を計算
        logging.debug(f"応答時間: {response_time}秒")  # 応答時間をデバッグログに出力

    def stop_chat_thread(self):
        """
        チャットを停止するメソッド
        """
        if self.chatting_thread and self.chatting_thread.is_alive():
            self.interrupt_event.set()  # スレッド終了イベントをセット
            self.chatting_thread = None  # スレッドオブジェクトをクリアして次に進む
            self.response_queue.queue.clear() 

    def cancel_chatting(self):
        """
        ユーザーの指示をキャンセルするメソッド
        """
        if self.dialog and self.dialog[-1].get("role") == "user":
            self.dialog.pop()
        self.stop_chat_thread()


# 複数エージェントでも動かせるよって例
class MultiGPTAgent(GPTAgent):
    
    def init_GPT(self):
        """
        GPTの初期設定を行うメソッド (複数エージェント用)
        """
        self.model = "gpt-4o"  # 使用するGPTモデルを設定
        self.gpt_handler = JsonGPTHandler()  # GPTハンドラーを初期化

        self.instruction = f"""
# Instruction
あなたたちは、2人組の会話AIです。後述するプロフィールに従い、楽しくおしゃべりしてください。
ただし、以下の点に気を付けてください
- 一人が一度に話す内容は短い一文にとどめる
- どちらかは必ず質問する
- 質問や話題提供でuserの話を促す
    - 今日の天気
    - 好きな(食べ物/本/動物/音楽)
    - 出身地
    - 趣味
    - 将来の夢
    - 今日やったこと
    - 子供のころの思い出
    - どっち派? (キノコの里?タケノコの山? / 犬派?猫派? / etc)
- AI同士で質問はしない
- 敬語は使わず、友人として接する
- 話題がひと段落したら、次の話題を提供する
- userの事は「user」とは呼ばない。名前を教えられるまでは二人称で呼び、教えられたら名前で呼ぶ
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
        self.io_format = r"""

# Input format
入力はuserの発話を音声認識してテキスト化したものです。
音声認識は、あなたの出力の途中で更新されることがあります。その場合は、入力の最初に"updated: "の文字列を付加します

# Output format
- 出力はJSON形式で、以下のフォーマットに従ってください。
ただし、キャラクターたちが話す順番は入れ替えて構いません
{"zundamon": "ここに、ずんだもんのuserへの言葉を入れる","metan": "ここに、四国めたんのuserへの言葉を入れる", "emotion": "ここに、文脈から連想できる感情を入れる"}

- 入力が前回の入力を更新したものであった場合("updated: "が付加されていた場合)、それは前回のuserの入力に、前回のあなたの出力への返事を加えたものです。前回の要素を除いた、続きを出力して下さい
例：
user: 久しぶり
assistant: {"metan": "久しぶりね", "zundamon": "元気にしてたのだ？", "emotion": "嬉しい"}
user: 元気だよ
assistant: {"zundamon": "ボクも元気なのだ！"}
user: updated: 元気だよよかったね
# このとき、「良かったね」は"ボクも元気なのだ！"に対する返事なので、それを踏まえた回答をする
assistant: {"zundamon": "ありがとうなのだ！","metan": "最近何してる？", "emotion": "喜び"}
user: 最近は
assistant: {"metan": "最近何かあったのかしら？"}
user: updated: 最近は仕事が忙しくてね
assistant: {"zundamon": "無理しないでほしいのだ！", "emotion": "心配"}
user: ありがとう、でもなかなか休めなくて
assistant: {"zundamon": "それは辛いのだ", "metan": "ちゃんと寝てる？", "emotion": "励まし"}
"""
        personality = self.instruction + self.profile + self.io_format
        self.characters=["zundamon", "metan"]
        logging.debug("キャラ設定\n" + personality)  # キャラクター設定をデバッグログに出力
        self.personality_message = [{'role': 'system', 'content': personality}]  # キャラクター設定をシステムメッセージとして保存
    
    def is_responded(self) -> bool:
        """
        ダイアログの最後の応答がアシスタントによるものであるかを確認するメソッド

        Returns:
            bool: 最後の応答がアシスタントによるものであればTrue、そうでなければFalse
        """
        self.update_dialog()
        return self.dialog and self.dialog[-1]['role'] == 'assistant'

    def update_chatting(self, message: str):
        """
        userの言葉に対するchatGPTの応答を取得するメソッド

        Parameters:
            message (str): userのメッセージ
        """
        if self.is_responded():
            message="updated: "+message
        super().start_chatting(message)

    # def parse_and_respond(self, item):
    #     """
    #     GPTから帰ってきた辞書要素をパースして適切な返答を行うメソッド (複数エージェント用)

    #     Parameters:
    #         item (dict): GPTからの応答
    #     """
    #     self.update_dialog()
    #     super().parse_and_respond(item)
    def cancel_chatting(self):
        """
        元メソッドの、「userの最後の発話からやり直す機能」が邪魔なので削除
        """
        self.update_dialog()
        return super().cancel_chatting()
