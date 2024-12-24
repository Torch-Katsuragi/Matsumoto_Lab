"""
採点のバイトのためのGPT処理
"""



import logging
from talk.gpt.gpt_fileprocess import GPTFileProcessor


def get_answer():
    """
    配布された模範解答から，回答部分だけを抜き出し
    """
    logging.basicConfig(level=logging.DEBUG)

    processor = GPTFileProcessor("gpt-4o")


    instructions = f"""
あなたは凄腕の教師です．
今からあなたに，採点のための模範解答が書かれた.ipynbファイルを処理してもらいます．
模範解答から回答のコードを抽出し，以下の採点項目に基づいて分け，それぞれのコードを出力してください．ただし，該当部分だけでなく，そこに至るまでに解答内に書いたコードも含めること
- 問1: tの値をヒストグラムを用いて可視化
- 問2: tの平均、標準偏差を求められているか
- 問3: ３シグマ法を用いて外れ値除去を行い、ヒストグラムを用いて可視化

"""
    output_field=r"""
    "問1の模範解答":"","問2の模範解答":""...}"""

    processed_text = processor.process_file(instructions,output_field)

    if processed_text:
        print(processed_text)
    return processed_text

def score(answer:str):
    """
    process_on_directoryメソッドのテスト関数
    """
    logging.basicConfig(level=logging.DEBUG)

    processor = GPTFileProcessor("gpt-4o")

    instructions = f"""
# 指示
あなたは凄腕の教師です．
今からあなたには，生徒が演習として提出した「.ipynbファイル」を採点してもらいます．
ファイル末尾の練習問題に，生徒が演習を行った痕跡が残っているはずです．

# 練習問題の採点項目
- 問1: tの値をヒストグラムを用いて可視化
- 問2: tの平均、標準偏差を求められているか
- 問3: ３シグマ法を用いて外れ値除去を行い、ヒストグラムを用いて可視化

# 模範解答
{answer}

# 注意事項
- 模範解答と合致するかではなく，問題の要件を満たしているかどうかを自分で判断すること
"""

    output_field={"模範解答との差異":"模範解答と生徒の回答の差異について考える","考察":"生徒の問題への理解度や，気づいたことなどを書く","Score 1":"1つ目の項目の正否 (0/1)","Score 2":"2つ目の項目の正否 (0/1)","Score 3":"3つ目の項目の正否 (0/1)"}

    processed_texts = processor.process_on_directory(instructions,output_field,extensions=[".ipynb"])




def main():
    answer=get_answer()
    score(answer)





if __name__=="__main__":
    main()