import os
import sys
import time
import base64
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion


# ============================================================
# THE FORGOTTEN SERVER
# A fictional, self-contained Linux CTF
# ============================================================

VERSION = "1.0.0"

INTRO = r"""
╔════════════════════════════════════════════════════════════╗
║                  THE FORGOTTEN SERVER                     ║
║                    Linux CTF - Easy                       ║
╚════════════════════════════════════════════════════════════╝

あなたはセキュリティ監査チームのメンバーだ。

ある企業から、長期間放置されている
社内研究用サーバーのセキュリティ調査を依頼された。

このサーバーは外部ネットワークから隔離されている。

しかし、管理者は数年前に退職しており、
現在の構成を把握している人物は誰もいない。

あなたに与えられた情報はこれだけだ。

    Target: lab-server

目的:

    [1] user.txt を取得する
    [2] root.txt を取得する

これは許可された検証環境である。

Good luck.

"""


# ============================================================
# GAME STATE
# ============================================================

START_TIME = time.time()

STATE = {
    "user_flag": False,
    "root_flag": False,

    "found_backup": False,
    "found_credentials": False,
    "found_history": False,
    "found_script": False,
    "checked_sudo": False,

    "root": False,

    "created_fake_tar": False,
    "executed_exploit": False,
}


# ============================================================
# VIRTUAL FILESYSTEM
# ============================================================

class Node:

    def __init__(
        self,
        name,
        node_type="dir",
        content="",
        owner="root",
        perm="755"
    ):
        self.name = name
        self.type = node_type
        self.content = content
        self.owner = owner
        self.perm = perm

        self.children = {}
        self.parent = None

    def add(self, node):
        node.parent = self
        self.children[node.name] = node


class VirtualFS:

    def __init__(self):

        self.root = self.build_filesystem()
        self.current = self.root
        self.user = "user"

    # --------------------------------------------------------
    # BUILD FILESYSTEM
    # --------------------------------------------------------

    def build_filesystem(self):

        root = Node("/")

        # ====================================================
        # /home
        # ====================================================

        home = Node("home")

        user = Node(
            "user",
            owner="user",
            perm="755"
        )

        # ----------------------------------------------------
        # README
        # ----------------------------------------------------

        user.add(
            Node(
                "README.txt",
                "file",
                """Welcome to the research server.

This machine has been abandoned.

The original administrator left behind
several maintenance scripts.

Some of the web application files were
also never removed.

If you are performing a security audit,
start with enumeration.

-- operations
""",
                owner="user"
            )
        )

        # ----------------------------------------------------
        # NOTES
        # ----------------------------------------------------

        user.add(
            Node(
                "notes.txt",
                "file",
                """Maintenance notes

The web application was migrated years ago.

Old backups:
    /var/www/html/backup/

Maintenance scripts:
    /opt/maintenance/

The backup system is still running.

I should really remove the old credentials
from the backup files.

-- admin
""",
                owner="user"
            )
        )

        # ----------------------------------------------------
        # BASH HISTORY
        # ----------------------------------------------------

        user.add(
            Node(
                ".bash_history",
                "file",
                """ls
cd /var/www/html
ls
cd backup
cat config.bak
cd /opt/maintenance
ls
cat backup.py
sudo -l
""",
                owner="user"
            )
        )

        # ----------------------------------------------------
        # user flag
        # ----------------------------------------------------

        user.add(
            Node(
                "user.txt",
                "file",
                "FORGOTTEN{first_access_7c91}\n",
                owner="user",
                perm="600"
            )
        )

        home.add(user)

        # ====================================================
        # /var/www/html
        # ====================================================

        var = Node("var")
        www = Node("www")
        html = Node("html")

        html.add(
            Node(
                "index.html",
                "file",
                """<html>
<head>
<title>Research Portal</title>
</head>

<body>

<h1>Internal Research Portal</h1>

<p>Server migration completed.</p>

<!-- TODO: remove backup directory -->

</body>
</html>
"""
            )
        )

        # ----------------------------------------------------
        # backup
        # ----------------------------------------------------

        backup = Node("backup")

        backup.add(
            Node(
                "config.bak",
                "file",
                """# Old configuration backup

APP_NAME=ResearchPortal
APP_ENV=production

DB_HOST=localhost
DB_USER=research
DB_PASS=summer_lab_2024

BACKUP_USER=backup
BACKUP_PATH=/var/backups

# TODO:
# Remove this file after migration.
"""
            )
        )

        backup.add(
            Node(
                "README.old",
                "file",
                """Old web application backup.

This directory should have been deleted
after the migration.

Apparently it wasn't.
"""
            )
        )

        html.add(backup)

        www.add(html)
        var.add(www)

        # ====================================================
        # /opt
        # ====================================================

        opt = Node("opt")
        maintenance = Node("maintenance")

        # ----------------------------------------------------
        # backup.py
        # ----------------------------------------------------

        maintenance.add(
            Node(
                "backup.py",
                "file",
                '''#!/usr/bin/env python3

import os

BACKUP_DIR = "/var/backups"

print("[*] Starting backup...")

os.system(
    "tar -czf /var/backups/site.tar.gz /var/www/html"
)

print("[+] Backup complete.")
''',
                perm="755"
            )
        )

        # ----------------------------------------------------
        # maintenance README
        # ----------------------------------------------------

        maintenance.add(
            Node(
                "README.txt",
                "file",
                """Maintenance scripts

backup.py
    Creates a compressed backup of the website.

The script is executed automatically by the
maintenance user.

DO NOT MODIFY THE SCRIPT.

-- administrator
"""
            )
        )

        opt.add(maintenance)

        # ====================================================
        # /etc
        # ====================================================

        etc = Node("etc")

        etc.add(
            Node(
                "hostname",
                "file",
                "lab-server\n"
            )
        )

        etc.add(
            Node(
                "motd",
                "file",
                """Research Server

Authorized personnel only.

This system is part of an internal
security research environment.
"""
            )
        )

        etc.add(
            Node(
                "passwd",
                "file",
                """root:x:0:0:root:/root:/bin/bash
user:x:1000:1000:user:/home/user:/bin/bash
research:x:1001:1001:research:/home/research:/bin/bash
backup:x:1002:1002:backup:/home/backup:/bin/bash
"""
            )
        )

        etc.add(
            Node(
                "sudoers",
                "file",
                """# simplified sudo configuration

user ALL=(root) NOPASSWD: /opt/maintenance/backup.py
"""
            )
        )

        # ====================================================
        # /var/log
        # ====================================================

        log = Node("log")

        log.add(
            Node(
                "auth.log",
                "file",
                """Sep 12 02:10:31 lab-server sudo: user : command=/opt/maintenance/backup.py
Sep 12 02:10:31 lab-server sudo: user : session opened
Sep 12 02:10:31 lab-server sudo: user : session closed

Sep 13 02:10:32 lab-server sudo: user : command=/opt/maintenance/backup.py
Sep 13 02:10:32 lab-server sudo: user : session opened
Sep 13 02:10:32 lab-server sudo: user : session closed

Sep 14 02:10:31 lab-server maintenance:
backup completed successfully
"""
            )
        )

        log.add(
            Node(
                "maintenance.log",
                "file",
                """Maintenance service

02:10 - backup started
02:10 - backup completed

The backup script requires tar.

No further action required.
"""
            )
        )

        var.add(log)

        # ====================================================
        # /var/backups
        # ====================================================

        backups = Node("backups")

        backups.add(
            Node(
                "README.txt",
                "file",
                """Backups are generated automatically.

Files older than 30 days are normally removed.
"""
            )
        )

        var.add(backups)

        # ====================================================
        # /tmp
        # ====================================================

        tmp = Node("tmp")

        tmp.add(
            Node(
                "debug.log",
                "file",
                """debug mode disabled

temporary maintenance information removed
"""
            )
        )

        root.add(tmp)

        # ====================================================
        # /root
        # ====================================================

        root_home = Node(
            "root",
            owner="root",
            perm="700"
        )

        root_home.add(
            Node(
                "root.txt",
                "file",
                "FORGOTTEN{root_maintenance_complete_91af}\n",
                owner="root",
                perm="600"
            )
        )

        root_home.add(
            Node(
                "README.txt",
                "file",
                """Congratulations.

You found the forgotten server.

The administrator assumed that a small
maintenance script could never become
a security problem.

They were wrong.

This machine was designed as a fictional
CTF environment.

Nothing here connects to a real system.
"""
            )
        )

        root.add(root_home)

        # ====================================================
        # ADD TOP LEVEL DIRECTORIES
        # ====================================================

        root.add(home)
        root.add(var)
        root.add(etc)
        root.add(opt)

        return root

    # --------------------------------------------------------
    # PWD
    # --------------------------------------------------------

    def pwd(self):

        node = self.current
        parts = []

        while node and node.name != "/":

            parts.append(node.name)
            node = node.parent

        return "/" + "/".join(reversed(parts))

    # --------------------------------------------------------
    # RESOLVE
    # --------------------------------------------------------

    def resolve(self, path):

        if not path:
            return self.current

        if path.startswith("/"):

            node = self.root
            parts = path.strip("/").split("/")

        else:

            node = self.current
            parts = path.split("/")

        for part in parts:

            if part in ("", "."):
                continue

            if part == "..":

                if node.parent:
                    node = node.parent

                continue

            if part not in node.children:
                return None

            node = node.children[part]

        return node

    # --------------------------------------------------------
    # LIST
    # --------------------------------------------------------

    def list_dir(self, node):

        return sorted(node.children.keys())


fs = VirtualFS()


# ============================================================
# UTILITY
# ============================================================

def clear_screen():

    print("\033[2J\033[H", end="")


def show_intro():

    clear_screen()
    print(INTRO)


def is_root():

    return fs.user == "root"


def permission_denied(node):

    if node.owner == "root" and not is_root():
        return True

    return False


# ============================================================
# COMMANDS
# ============================================================

def cmd_pwd(args):

    print(fs.pwd())


def cmd_ls(args):

    node = fs.current

    if args:

        node = fs.resolve(args[0])

        if not node or node.type != "dir":

            print("ls: cannot access: No such file or directory")
            return

    if permission_denied(node):

        print("Permission denied")
        return

    for name in fs.list_dir(node):

        child = node.children[name]

        if child.type == "dir":

            print(f"{name}/")

        else:

            print(name)


def cmd_cd(args):

    if not args:

        fs.current = fs.root
        return

    node = fs.resolve(args[0])

    if not node or node.type != "dir":

        print("cd: No such directory")
        return

    if permission_denied(node):

        print("Permission denied")
        return

    fs.current = node


def cmd_cat(args):

    if not args:

        print("usage: cat <file>")
        return

    node = fs.resolve(args[0])

    if not node or node.type != "file":

        print("cat: No such file")
        return

    if permission_denied(node):

        print("Permission denied")
        return

    print(node.content)

    path = fs.pwd()

    if node.name == "config.bak":

        STATE["found_backup"] = True
        STATE["found_credentials"] = True

    if node.name == ".bash_history":

        STATE["found_history"] = True

    if node.name == "backup.py":

        STATE["found_script"] = True

    if node.name == "user.txt":

        STATE["user_flag"] = True

    if node.name == "root.txt":

        STATE["root_flag"] = True


def cmd_id(args):

    if is_root():

        print(
            "uid=0(root) gid=0(root) "
            "groups=0(root)"
        )

    else:

        print(
            "uid=1000(user) gid=1000(user) "
            "groups=1000(user)"
        )


def cmd_whoami(args):

    print(fs.user)


def cmd_hostname(args):

    print("lab-server")


def cmd_env(args):

    print("PATH=/usr/local/bin:/usr/bin:/bin")
    print("USER=user")
    print("HOME=/home/user")
    print("HOSTNAME=lab-server")


def cmd_sudo(args):

    STATE["checked_sudo"] = True

    if not args:

        print(
            "usage: sudo -l"
        )
        return

    if args[0] == "-l":

        print(
            "Matching Defaults entries for user on lab-server:"
        )

        print()

        print(
            "User user may run the following commands "
            "on lab-server:"
        )

        print()

        print(
            "    (root) NOPASSWD: "
            "/opt/maintenance/backup.py"
        )

        return

    # --------------------------------------------------------
    # Execute backup script
    # --------------------------------------------------------

    if args[0] == "/opt/maintenance/backup.py":

        cmd_backup(args[1:], sudo=True)
        return

    print(
        "sudo: command not permitted"
    )


def cmd_find(args):

    if not args:

        start = fs.current
        base = fs.pwd()

    else:

        start = fs.resolve(args[0])
        base = args[0]

    if not start:

        print("find: path not found")
        return

    if permission_denied(start):

        print("Permission denied")
        return

    def walk(node, path):

        print(path)

        if node.type != "dir":
            return

        for child in sorted(
            node.children.values(),
            key=lambda x: x.name
        ):

            if child.owner == "root" and not is_root():

                continue

            child_path = (
                path.rstrip("/") +
                "/" +
                child.name
            )

            walk(child, child_path)

    walk(start, base)


def cmd_grep(args):

    if len(args) < 2:

        print(
            "usage: grep <pattern> <file>"
        )

        return

    pattern = args[0]
    node = fs.resolve(args[1])

    if not node or node.type != "file":

        print(
            "grep: No such file"
        )

        return

    if permission_denied(node):

        print("Permission denied")
        return

    for line in node.content.splitlines():

        if pattern.lower() in line.lower():

            print(line)


def cmd_clear(args):

    show_intro()


# ============================================================
# PYTHON
# ============================================================

def cmd_python(args):

    if not args:

        print("Python 3.12.0")
        print(
            "Interactive interpreter is simulated."
        )
        return

    if "-c" not in args:

        print(
            "Python interpreter closed."
        )

        return

    command = " ".join(args)

    # --------------------------------------------------------
    # Simulated shell escape
    # --------------------------------------------------------

    shell_patterns = [

        "import os",
        "os.system",
        "os.execl",
        "subprocess",
    ]

    if any(
        pattern in command
        for pattern in shell_patterns
    ):

        if STATE["checked_sudo"]:

            fs.user = "root"
            STATE["root"] = True

            print()
            print(
                "[+] Python executed with elevated privileges."
            )

            print(
                "[+] Privilege escalation successful."
            )

            print(
                "[+] uid=0(root)"
            )

            print()

        else:

            print(
                "Python executed, but the process "
                "does not have elevated privileges."
            )

        return

    print(
        "Python interpreter closed."
    )


# ============================================================
# BACKUP / PATH HIJACK SIMULATION
# ============================================================

def cmd_touch(args):

    if not args:

        print("usage: touch <file>")
        return

    filename = args[0]

    if filename == "tar":

        STATE["created_fake_tar"] = True

        print(
            f"created: {filename}"
        )

        return

    print(
        f"touch: created {filename}"
    )


def cmd_chmod(args):

    if len(args) < 2:

        print(
            "usage: chmod <mode> <file>"
        )

        return

    print(
        f"mode changed: {args[1]}"
    )


def cmd_export(args):

    if len(args) != 1 or "=" not in args[0]:

        print(
            "usage: export NAME=value"
        )

        return

    name, value = args[0].split("=", 1)

    if name == "PATH":

        if STATE["created_fake_tar"]:

            STATE["executed_exploit"] = True

            print(
                "[+] PATH modified."
            )

            print(
                "[+] A privileged script uses an "
                "unqualified executable."
            )

            print(
                "[+] This may be exploitable."
            )

        else:

            print(
                "PATH updated."
            )

    else:

        print(
            f"{name} exported."
        )


# ============================================================
# HINT SYSTEM
# ============================================================

def cmd_hint(args):

    # --------------------------------------------------------
    # Initial enumeration
    # --------------------------------------------------------

    if not STATE["found_backup"]:

        print(
            "HINT: READMEやnotes.txtを読んで、"
            "Web関連のディレクトリを探してみよう。"
        )

        return

    # --------------------------------------------------------

    if not STATE["found_credentials"]:

        print(
            "HINT: /var/www/html/backup/ に"
            "古いファイルが残っている。"
        )

        return

    # --------------------------------------------------------

    if not STATE["found_history"]:

        print(
            "HINT: userの操作履歴を確認してみよう。"
        )

        return

    # --------------------------------------------------------

    if not STATE["found_script"]:

        print(
            "HINT: /opt/maintenance/ に"
            "何かスクリプトがある。"
        )

        return

    # --------------------------------------------------------

    if not STATE["checked_sudo"]:

        print(
            "HINT: 現在のユーザーがrootとして"
            "実行できるコマンドを確認しよう。"
        )

        return

    # --------------------------------------------------------

    if not STATE["root"]:

        print(
            "HINT: sudoで実行できるのはPythonスクリプト。"
            "スクリプトの内容をよく読もう。"
        )

        return

    # --------------------------------------------------------

    if not STATE["user_flag"]:

        print(
            "HINT: user.txtは自分のホームディレクトリにある。"
        )

        return

    # --------------------------------------------------------

    if not STATE["root_flag"]:

        print(
            "HINT: root権限を取得したなら、"
            "/rootを調べよう。"
        )

        return

    print(
        "HINT: もうすべてのフラグを取得している。"
    )


# ============================================================
# SCORE
# ============================================================

def show_status():

    elapsed = int(
        time.time() - START_TIME
    )

    print()
    print(
        "========== STATUS =========="
    )

    print(
        f"User flag : "
        f"{'OWNED' if STATE['user_flag'] else '---'}"
    )

    print(
        f"Root      : "
        f"{'YES' if STATE['root'] else 'NO'}"
    )

    print(
        f"Root flag : "
        f"{'OWNED' if STATE['root_flag'] else '---'}"
    )

    print(
        f"Time      : {elapsed}s"
    )

    print(
        "============================"
    )


# ============================================================
# HELP
# ============================================================

def cmd_help(args):

    print(
        """
Available commands:

  pwd
  ls
  cd
  cat
  find
  grep

  id
  whoami
  hostname
  env

  sudo
  python3
  python

  touch
  chmod
  export

  hint
  status
  clear
  help
"""
    )


# ============================================================
# COMMAND TABLE
# ============================================================

COMMANDS = {

    "pwd": cmd_pwd,
    "ls": cmd_ls,
    "cd": cmd_cd,
    "cat": cmd_cat,
    "find": cmd_find,
    "grep": cmd_grep,

    "id": cmd_id,
    "whoami": cmd_whoami,
    "hostname": cmd_hostname,
    "env": cmd_env,

    "sudo": cmd_sudo,

    "python": cmd_python,
    "python3": cmd_python,

    "touch": cmd_touch,
    "chmod": cmd_chmod,
    "export": cmd_export,

    "hint": cmd_hint,
    "status": lambda args: show_status(),
    "clear": cmd_clear,
    "help": cmd_help,
}


# ============================================================
# TAB COMPLETION
# ============================================================

class GameCompleter(Completer):

    def get_completions(
        self,
        document,
        complete_event
    ):

        text = document.text_before_cursor
        parts = text.split()

        # ----------------------------------------------------
        # command completion
        # ----------------------------------------------------

        if len(parts) <= 1:

            word = parts[0] if parts else ""

            for command in sorted(COMMANDS):

                if command.startswith(word):

                    yield Completion(
                        command,
                        start_position=-len(word)
                    )

            return

        # ----------------------------------------------------
        # path completion
        # ----------------------------------------------------

        word = parts[-1]

        if "/" in word:

            if word.startswith("/"):

                parent_path, prefix = word.rsplit(
                    "/",
                    1
                )

                node = fs.resolve(
                    parent_path or "/"
                )

            else:

                full = fs.pwd() + "/" + word

                parent_path, prefix = full.rsplit(
                    "/",
                    1
                )

                node = fs.resolve(parent_path)

        else:

            node = fs.current
            prefix = word

        if not node or node.type != "dir":
            return

        for name in fs.list_dir(node):

            child = node.children[name]

            if permission_denied(child):
                continue

            if name.startswith(prefix):

                yield Completion(
                    name,
                    start_position=-len(prefix)
                )


# ============================================================
# START
# ============================================================

session = PromptSession(
    completer=GameCompleter()
)

show_intro()


# ============================================================
# MAIN LOOP
# ============================================================

while True:

    if fs.user == "root":

        prompt = "root@lab-server# "

    else:

        prompt = "user@lab-server$ "

    try:

        command = session.prompt(
            prompt
        ).strip()

    except KeyboardInterrupt:

        print(
            "\nUse 'exit' to leave the challenge."
        )

        continue

    except EOFError:

        print()
        break

    if not command:
        continue

    # --------------------------------------------------------
    # Exit
    # --------------------------------------------------------

    if command == "exit":

        print(
            "\nChallenge terminated."
        )

        break

    # --------------------------------------------------------
    # Parse
    # --------------------------------------------------------

    parts = command.split()

    name = parts[0]
    args = parts[1:]

    # --------------------------------------------------------
    # Execute
    # --------------------------------------------------------

    fn = COMMANDS.get(name)

    if fn:

        fn(args)

    else:

        print(
            f"{name}: command not found"
        )

    # --------------------------------------------------------
    # Win condition
    # --------------------------------------------------------

    if (
        STATE["user_flag"]
        and STATE["root_flag"]
    ):

        elapsed = int(
            time.time() - START_TIME
        )

        print()
        print(
            "╔══════════════════════════════════════════╗"
        )
        print(
            "║              MACHINE PWNED              ║"
        )
        print(
            "╚══════════════════════════════════════════╝"
        )

        print()
        print(
            f"TIME: {elapsed}s"
        )

        print()
        print(
            "You compromised the forgotten server."
        )

        print(
            "Both flags have been captured."
        )

        print()

        break