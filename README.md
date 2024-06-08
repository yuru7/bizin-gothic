# Bizin Gothic (ビジン ゴシック)

Bizin Gothic (ビジン ゴシック) は、ユニバーサルデザインフォントの [BIZ UDゴシック](https://github.com/googlefonts/morisawa-biz-ud-gothic) と、英文フォントの [Inconsolata](https://github.com/googlefonts/inconsolata) を合成した、プログラミング向けフォントです。

BIZ UDゴシックの目に優しく馴染む字形と Inconsolata の癖がなく美しい字形を違和感無く組み合わせることを目指しています。

[👉 ダウンロード](https://github.com/yuru7/bizin-gothic/releases/latest)  
※「Assets」内の zip ファイルをダウンロードしてご利用ください。

> 💡 その他、公開中のプログラミングフォント
> - 日本語文字に源柔ゴシック、英数字部分に Hack を使った [**白源 (はくげん／HackGen)**](https://github.com/yuru7/HackGen)
> - 日本語文字に IBM Plex Sans JP、英数字部分に IBM Plex Mono を使った [**PlemolJP (プレモル ジェイピー)**](https://github.com/yuru7/PlemolJP)
> - 日本語文字にBIZ UDゴシック、英数字部分に JetBrains Mono を使った [**UDEV Gothic**](https://github.com/yuru7/udev-gothic)

## 特徴

以下の特徴を備えています。

- モリサワ社の考えるユニバーサルデザインが盛り込まれたBIZ UDゴシック由来の読み易い日本語文字
- [Ricty](https://rictyfonts.github.io/) でも合成元として用いられている Inconsolata 由来の綺麗なラテン文字
- 半角1:全角2 幅の等幅フォント
- BIZ UDゴシック相当の IVS (異体字シーケンス) に対応
- コーディング中に気付きづらい全角スペースの可視化
- 判読性向上のための細かな修正
  - チルダ (半角波線) の曲線を強調
  - シングルクォート `'` 、ダブルクォート `"` 、バッククォート `` ` `` 、コロン `:` 、セミコロン `;` 、カンマ `,` 、ドット `.` を拡大
  - 一部の全角括弧類で位置調整
  - `ぱぴぷぺぽパピプペポ` の半濁点を強調
  - カ力 エ工 ロ口 ー一 ニ二 (カタカナ・漢字) へヘ (ひらがな・カタカナ) `～〜` (全角チルダ・波ダッシュ) の区別
- 文字の調和よりも判読性を優先した、Ricty インスパイアな Discord バリエーション
  - `07DZlrz|` の字形を変更
  - 前述の拡大している記号をさらに拡大

## 表示サンプル

| 通常版 | Discord |
| :---: | :---: |
| ![image](https://github.com/yuru7/bizin-gothic/assets/13458509/eaa7d3c6-7cee-4d12-920a-77cd72a40c42) | ![image](https://github.com/yuru7/bizin-gothic/assets/13458509/66403c9c-8cec-4fd4-baf9-f6b4679b6636) |

## ビルド

- fontforge: `20230101` \[[Windows](https://fontforge.org/en-US/downloads/windows/)\] \[[Linux](https://fontforge.org/en-US/downloads/gnulinux/)\]
- Python: `>=3.8`

### Windows (PowerShell)

```sh
# 必要パッケージのインストール
pip install -r requirements.txt
# ビルド
& "C:\Program Files (x86)\FontForgeBuilds\bin\ffpython.exe" .\fontforge_script.py && python .\fonttools_script.py
```

## ライセンス

SIL Open Font License, Version 1.1 が適用され、個人・商用問わず利用可能です。

ソースフォントのライセンスも同様に SIL Open Font License, Version 1.1 が適用されています。詳しくは `source_fonts` ディレクトリに含まれる `LICENSE` ファイルを参照してください。
