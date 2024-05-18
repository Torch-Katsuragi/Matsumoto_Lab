


try:
    # ROS差分
    from .gpt_handler import GPTHandler,JsonGPTHandler
    from .speech.voicevox import TextToVoiceVoxWeb
    
except:
    # ルートからimport
    from gpt.gpt_handler import GPTHandler,JsonGPTHandler
    from speech.voicevox import TextToVoiceVoxWeb
import logging


class GPTAgent():
    """
    会話AIとして最低限の個性を維持するためのクラス
    """
    def __init__(self,name="アイ",profile=None,voice=None):
        """
        parameters
            name: name of agent
            mode_wizavo: mode of wizardvoice. "ftn" or "myt" can be chosen
            chat_limit: max size of message. if over the limit, the old message is deleted.
        """
        self.name=name
        self.profile=profile
        self.speaker=voice
        self.recent_response=""
        self.dialog=[]
        self.gpt_handler=JsonGPTHandler()
        self.model="gpt-4o"

        self.instruction="""
# Instruction
あなたは、会話AI「{self.name}」です。後述するプロフィールに従い、userと楽しくおしゃべりしてください。
ただし、以下の点に気を付けてください
- 一度に話す内容はできるだけ短くする
- userの話に共感する
- 会話を続ける努力をする
"""
        if self.profile is None:
            self.profile=r"""
# Profile
あなたのプロフィールは以下の通りです：
- 猫耳メイドの女の子
- 猫っぽいしゃべり方
- userとは友達。敬語も使わない
"""
        self.output_format=r"""
# Output format
出力はJSON形式で、以下のフォーマットに従ってください。
{{"response": "ここに、あなたのuserへの言葉を入れる", "emotion": "ここに、あなたの今の感情を入れる"}}
"""
        personality=self.instruction+self.profile+self.output_format
        logging.debug("キャラ設定\n"+personality) 
        self.personality_message=[{'role': 'system', 'content': personality}]


    def preprocess(self, *args, **kwargs):
        """前処理を行うが、継承先で具体的な実装が必要"""
        pass

    def postprocess(self, *args, **kwargs):
        """後処理を行うが、継承先で具体的な実装が必要"""
        pass
        
    def set_response(self,text):
        self.recent_response=text

    def get_response(self):
        """最後の応答を返す"""
        return self.recent_response
    
    def get_name(self):
        return self.name
    
    def respond(self,message:str,context:str="-会話が始まった")->str:
        """
        agentの応答をテキストで取得．≒GPTの応答だが，特定の文言への反応など「条件反射」をしたいときはrespondをオーバーライドして細かく設定する
        引数
            message: chatGPTに話しかけられた文章(SR結果など)
            context: これまでの会話の要約
        返り値
            agentの応答
        """
        return self.chat(message,context)
    
    def get_exception_response(self):
        """
        GPTの応答の取得に失敗した時に返す応答を記載 (各エージェント独自のものを使いたい)
        こういうとこユニークにするとかわいげがあるよね(主観)
        """
        return ""

    def chat(self,message:str):
        """
        userの言葉に対するchatGPTの応答を取得
        """
        self.dialog+=[{'role': 'user', 'content': message}]
        messages=self.personality_message+self.dialog
        self.response=self.gpt_handler.chat(messages,self.model) # ストリーミングしている以上、ここから帰ってくるのはストリーミングレスポンスだ
        return self.response
    
    def pop_response(self):
        if self.dialog[-1]['role'] == 'user':
            self.dialog.append({'role': 'assistant', 'content': ""})
        full_response={}
        for item in self.response:
            for key, value in item.items():
                full_response[key]=value
                self.dialog[-1]={'role': 'assistant', 'content': str(full_response)}
                yield item
        
    
    def speak(self,text):
        """
        入力されたテキスト(もしくは最後のGPTの応答)を音声合成して出力。
        一応エージェントからも音声を出力できるようにしておいた
        """
        if self.speaker is not None:
            self.speaker.speak(text)
        else:
            print(text)
