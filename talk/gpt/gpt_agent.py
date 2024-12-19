

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

    def __init__(self, name="アイ", profile=None, speakers=[],log_title:str="",log_directory=""):
        """
        コンストラクタ

        Parameters:
            name (str): エージェントの名前。デフォルトは"アイ"。
            profile (str): エージェントのプロフィール。Noneの場合はデフォルトのプロフィールを使用。
            speakers (list): 音声合成用のスピーカーリスト。空リストの場合は音声合成は行われない。
            log_title (str): ログファイルのタイトル。
            log_directory (str): ログファイルの出力ディレクトリ。例: "./path/to/log/directory"。
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
        self.date=time.strftime('%Y%m%d_%H%M')
        self.log_title=log_title
        self.log_directory=log_directory
        self._log_lock = threading.Lock() # dialogのアクセス競合防止用のlock

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
        self.sys_message = [{'role': 'system', 'content': personality}]  # キャラクター設定をシステムメッセージとして保存

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
    

    def put_dialog(self,role:str,content)->bool:
        """
        chatgptとのmessageをself.dialogに追加するメソッド

        Parameters:
            role (str): メッセージのロール（"sys","user"または"assistant"）。
            message (str or dict): メッセージの内容。文字列または辞書型。

        Returns:
            bool: メッセージが追加された場合はTrue、そうでない場合はFalse。
        """
        with self._log_lock:
            logging.debug("dialog updated: %s,%s", role, content)  # ダイアログが更新されたことをデバッグログに出力
            if self.dialog and self.dialog[-1]['role'] == role:
                # roleが同一の場合、最後の要素のcontentを取得
                last_content = self.dialog[-1]['content']
                # contentが辞書形式の文字列であるか確認し、辞書に変換
                last_dict = eval(last_content) if last_content.startswith('{') and last_content.endswith('}') else {}
                if last_dict and isinstance(content, dict):
                    # 最後の要素が辞書型で、messageも辞書型の場合、既存の辞書にmessageを追加
                    last_dict.update(content)
                    self.dialog[-1]['content'] = str(last_dict)
                elif not last_dict and isinstance(content, str):
                    # 最後の要素が辞書型ではなく、messageが文字列型の場合、既存の文字列にmessageを追加
                    self.dialog[-1]['content'] += content
                else:
                    # 上記以外の場合、新しい要素として追加
                    self.dialog.append({'role': role, 'content': str(content)})
            else:
                # ダイアログにアシスタントの応答を追加
                self.dialog.append({'role': role, 'content': str(content)})
        # 自動バックアップ
        self.save_dialog(log_title="autosave")
        return bool(content)
    
    def get_dialog(self, contain_sys=False) -> list:
        """
        現在の会話ログを取得するメソッド

        Returns:
            list: 現在の会話ログ
        """
        dialog=[]
        with self._log_lock:
            if contain_sys:
                dialog = self.sys_message + self.dialog
            else:
                dialog = self.dialog
        return dialog
    
    def get_recent_output(self)->str:
        """
        self.dialogの中で、roleが"assistant"である要素のうち、最新のものを返すメソッド。

        Returns:
            dict: 最新のassistantの出力。要素が存在しない場合はNoneを返す。
        """
        with self._log_lock:
            for i in range(len(self.dialog)-1,-1,-1):
                if self.dialog[i]['role'] == 'assistant':
                    return self.dialog[i]['content']
            return None
    
    def save_dialog(self,log_title="",log_directory=""):
        """
        現在の会話ログを.txtファイルに保存するメソッド
        """
        import os
        try:
            # ファイル名決定
            if log_title:
                title=log_title
            elif self.log_title:
                title=self.log_title
            else:
                title="NoTitle"
            
            # 保存先決定
            if log_directory:
                directory = log_directory
            elif self.log_directory:
                directory=self.log_directory
            else:
                directory = ".user_data/log"
            
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            # 現在の日時とタイトルを使ってファイルパスを作成し、書き込みモードで開く
            file_path = f"{directory}/{self.date}_{title}.txt"
            with open(file_path, "w", encoding="utf-8") as file:
                # ダイアログの各エントリをファイルに書き込む
                for entry in self.get_dialog(contain_sys=True):
                    file.write(f"{entry}\n")
            logging.debug("ダイアログの保存に成功しました。")  # 保存成功のデバッグログ
        except Exception as e:
            logging.debug("ダイアログの保存に失敗しました: %s", e)  # 保存失敗のエラーログ

    def start_chatting(self, message: str):
        """
        userの言葉に対するchatGPTの応答を取得するメソッド
        Parameters:
            message (str): userのメッセージ
        """
        self.put_dialog('user', message)  # ダイアログにユーザーのメッセージを追加
        self.save_dialog(log_title="autosave") # 更新したダイアログをログファイルにも反映

        gpt_handler = JsonGPTHandler()  # GPTハンドラーを初期化
        messages = self.sys_message + self.dialog  # メッセージリストを作成
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
                self.put_dialog('assistant',item)
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
            self.parse_and_respond(item)  # 応答アイテムをパースして返答
            if interrupt_event.is_set():  # 中断イベントがセットされているか確認
                return
            self.response_queue.put(item)  # 応答アイテムをキューに追加
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
        with self._log_lock:
            if self.dialog and self.dialog[-1].get("role") == "user":
                self.dialog.pop()
            self.stop_chat_thread()

    def reset(self):
        """
        会話ログなどをリセット
        """
        self.put_dialog()
        self.dialog=[]


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
        self.sys_message = [{'role': 'system', 'content': personality}]  # キャラクター設定をシステムメッセージとして保存
    
    def is_responded(self) -> bool:
        """
        ダイアログの最後の応答がアシスタントによるものであるかを確認するメソッド

        Returns:
            bool: 最後の応答がアシスタントによるものであればTrue、そうでなければFalse
        """
        self._log_lock.acquire()
        try:
            return bool(self.dialog) and self.dialog[-1]['role'] == 'assistant'
        finally:
            self._log_lock.release()

    def update_chatting(self, message: str):
        """
        userの言葉に対するchatGPTの応答を取得するメソッド

        Parameters:
            message (str): userのメッセージ
        """
        if self.is_responded():
            message="updated: "+message
        self.start_chatting(message)


    # def cancel_chatting(self):
    #     """
    #     元メソッドの、「userの最後の発話からやり直す機能」が邪魔なので削除
    #     """
    #     self.put_dialog()
    #     return super().cancel_chatting()
