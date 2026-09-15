# The Forgotten Server

**The Forgotten Server** は、Pythonで実装された自己完結型のLinux CTFシミュレータです。

プレイヤーは低権限ユーザーとしてサーバーを調査し、隠された情報や脆弱性を発見してroot権限を取得することを目指します。

> **難易度:** Easy
> **カテゴリ:** Linux / CTF / 権限昇格
> **実装:** Python
> **環境:** 完全シミュレーション

---

## 概要

古い社内研究サーバーを調査し、情報収集から権限昇格までの攻撃経路を組み立てます。

主な攻略要素：

```text
Enumeration
    ↓
Information Gathering
    ↓
sudo Enumeration
    ↓
Vulnerability Discovery
    ↓
PATH Hijacking
    ↓
Root
```

---

## 特徴

* Linuxファイルシステムのシミュレーション
* Linux風コマンド
* ファイル・ディレクトリ列挙
* `find` / `grep`
* `sudo -l`
* PATH操作
* PATH Hijacking
* user / rootフラグ
* ヒント機能
* 進行状況確認
* 外部ネットワーク通信なし
* ホストOSへの影響なし

---

## 必要環境

* Python 3.10以上
* `prompt_toolkit`

```bash
pip install -r requirements.txt
```

---

## 起動方法

```bash
git clone https://github.com/aaa3141592/the-forgotten-server.git
cd the-forgotten-server
pip install -r requirements.txt
python3 main.py
```

---

## 使用できるコマンド

```text
pwd
ls
cd
cat
find
grep
whoami
id
hostname
env
echo
which
export
touch
chmod
sudo
python
status
hint
help
clear
exit
```

すべての操作はシミュレータ内部で処理されます。

---

## 目的

以下の2つのフラグを取得してください。

```text
user.txt
root.txt
```

最終目標はroot権限を取得し、`/root/root.txt` を読み取ることです。

---

## 学習内容

* Linux Enumeration
* Information Gathering
* sudo Enumeration
* PATH Hijacking
* Linux権限昇格の基本
* CTFにおける攻撃経路の組み立て

---

## 自動化・研究用途

完全にシミュレーションされた環境のため、LLMやセキュリティエージェントの実験にも利用できます。

* LLMによるCTF攻略
* 自動Linux列挙
* 自動権限昇格
* 攻撃経路の自動判断
* セキュリティエージェントの評価
* 再現可能なセキュリティ実験

---

## ファイル構成

```text
the-forgotten-server/
├── main.py
├── README.md
├── requirements.txt
└── walkthrough.md
```

`walkthrough.md` に想定攻略ルートを記載しています。

**自力で攻略したい場合は、先に読まないことを推奨します。**

---

## セキュリティについて

本プロジェクトは教育・研究目的のCTFシミュレータです。

実際のLinux環境やホストOSに対する攻撃・権限昇格は行いません。

---

## 作者

GitHub: `aaa3141592`
