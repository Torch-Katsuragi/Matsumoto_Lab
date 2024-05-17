# 松本のラボ

このリポジトリは、私がいろいろ新しいものを試すために作りました。

リポジトリの管理としてあまり上手いやり方ではないんですが、乱立すると管理が大変だなって。

主に便利ツールとかを作る作業場として機能させるつもりです。


## セットアップ

以下の手順に従ってセットアップと実行を行ってください。

### 環境変数の設定

`.env`ファイルを作成し、`.env.sample`を参考にしてAPIキーを設定してください。

voicevox api：https://voicevox.su-shiki.com/su-shikiapis/

他は、わざわざ説明する必要はないでしょう。
   ```
   OPENAI_API_KEY=your_openai_api_key
   VOICEVOX_API_KEY=your_voicevox_api_key
   GOOGLE_APPLICATION_CREDENTIALS=path_to_your_google_credentials_json
   ```

### 環境構築

setup.ps1を参考にしてください。なにかモジュールが足りないよって言われたら自分でダウンロードして下さい


## 内容物

### parroting.py

parroting.pyは、音声認識を使用して入力された音声をそのまま音声合成で出力するスクリプトです。このスクリプトは、Google Cloud Speech-to-TextとVOICEVOXを使用しています。
もちろん、このままでは何の意味もないのでうまく自分のプロジェクトに取り入れて価値創造しましょう。