from __future__ import annotations

import shlex
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout


# ============================================================
# Game State
# ============================================================

STATE = {
    "checked_sudo": False,
    "found_backup": False,
    "found_script": False,
    "created_fake_tar": False,
    "executed_exploit": False,
    "root": False,
    "path": "/usr/local/bin:/usr/bin:/bin",
    "start_time": time.time(),
}


# ============================================================
# Virtual Filesystem
# ============================================================

@dataclass
class Node:
    name: str
    node_type: str = "file"
    content: str = ""
    owner: str = "user"
    perm: int = 0o644
    children: Dict[str, "Node"] = field(default_factory=dict)


class VirtualFS:
    def __init__(self):
        self.user = "user"
        self.cwd = "/home/user"

        self.root = Node(
            name="/",
            node_type="dir",
            owner="root",
            perm=0o755,
        )

        self._build_filesystem()

    # --------------------------------------------------------
    # Filesystem construction
    # --------------------------------------------------------

    def _mkdir(
        self,
        path: str,
        owner: str = "root",
        perm: int = 0o755,
    ) -> Node:
        parts = self._split(path)
        current = self.root

        for part in parts:
            if part not in current.children:
                current.children[part] = Node(
                    name=part,
                    node_type="dir",
                    owner=owner,
                    perm=perm,
                )

            current = current.children[part]

        return current

    def _mkfile(
        self,
        path: str,
        content: str = "",
        owner: str = "root",
        perm: int = 0o644,
    ) -> Node:
        parts = self._split(path)

        if not parts:
            raise ValueError("Invalid file path")

        parent_parts = parts[:-1]
        filename = parts[-1]

        current = self.root

        for part in parent_parts:
            if part not in current.children:
                current.children[part] = Node(
                    name=part,
                    node_type="dir",
                    owner=owner,
                    perm=0o755,
                )

            current = current.children[part]

        current.children[filename] = Node(
            name=filename,
            node_type="file",
            content=content,
            owner=owner,
            perm=perm,
        )

        return current.children[filename]

    def _build_filesystem(self):
        # ----------------------------------------------------
        # Directories
        # ----------------------------------------------------

        directories = [
            "/home",
            "/home/user",
            "/var",
            "/var/www",
            "/var/www/html",
            "/var/www/html/backup",
            "/var/backups",
            "/var/log",
            "/opt",
            "/opt/maintenance",
            "/etc",
            "/tmp",
            "/usr",
            "/usr/bin",
            "/usr/local",
            "/usr/local/bin",
            "/bin",
            "/root",
        ]

        for directory in directories:
            owner = "root"

            if directory.startswith("/home/user"):
                owner = "user"

            self._mkdir(directory, owner=owner)

        # ----------------------------------------------------
        # User files
        # ----------------------------------------------------

        self._mkfile(
            "/home/user/README.txt",
            """Welcome to the internal research server.

Your account has limited privileges.

Useful commands:
  ls
  cd
  cat
  find
  grep
  sudo
  python
  which
  export

The objective is to investigate the system and recover
the user and root flags.
""",
            owner="user",
        )

        self._mkfile(
            "/home/user/notes.txt",
            """Maintenance notes:

- The web application was backed up regularly.
- Old backups were moved into the web directory.
- The maintenance team used a Python script under /opt.
- Some old configuration files may still contain useful information.

Do not delete anything until the investigation is complete.
""",
            owner="user",
        )

        self._mkfile(
            "/home/user/.bash_history",
            """ls
cat notes.txt
cd /var/www/html
ls
cd backup
ls
cat config.bak
cd /opt/maintenance
ls
cat backup.py
sudo -l
which tar
""",
            owner="user",
            perm=0o600,
        )

        self._mkfile(
            "/home/user/user.txt",
            "FORGOTTEN{first_access_7c91}\n",
            owner="user",
            perm=0o644,
        )

        # ----------------------------------------------------
        # Web application
        # ----------------------------------------------------

        self._mkfile(
            "/var/www/html/index.html",
            """<!DOCTYPE html>
<html>
<head>
    <title>Research Portal</title>
</head>
<body>
    <h1>Internal Research Portal</h1>
    <p>Legacy application.</p>
</body>
</html>
""",
            owner="root",
            perm=0o644,
        )

        # ----------------------------------------------------
        # Old backup
        # ----------------------------------------------------

        self._mkfile(
            "/var/www/html/backup/config.bak",
            """# Old application configuration
# Archived during migration

APP_NAME=research-portal
APP_ENV=production

DB_HOST=localhost
DB_USER=research
DB_PASSWORD=summer_lab_2024

BACKUP_ENABLED=true
BACKUP_SCRIPT=/opt/maintenance/backup.py
""",
            owner="root",
            perm=0o644,
        )

        self._mkfile(
            "/var/www/html/backup/README.old",
            """Old backup directory.

This directory is no longer used by the current application.

Maintenance scripts are stored under /opt/maintenance.
""",
            owner="root",
            perm=0o644,
        )

        # ----------------------------------------------------
        # Maintenance script
        # ----------------------------------------------------

        self._mkfile(
            "/opt/maintenance/backup.py",
            """#!/usr/bin/env python3

import os

BACKUP_DIR = "/var/backups"

print("[*] Starting backup...")

os.system(
    "tar -czf /var/backups/site.tar.gz /var/www/html"
)

print("[+] Backup complete.")
""",
            owner="root",
            perm=0o755,
        )

        self._mkfile(
            "/opt/maintenance/README.txt",
            """Maintenance utilities.

The backup process is automated and should normally be run
through the approved sudo configuration.
""",
            owner="root",
            perm=0o644,
        )

        # ----------------------------------------------------
        # System files
        # ----------------------------------------------------

        self._mkfile(
            "/etc/hostname",
            "lab-server\n",
            owner="root",
            perm=0o644,
        )

        self._mkfile(
            "/etc/motd",
            """Authorized personnel only.

This system is part of the internal research environment.
""",
            owner="root",
            perm=0o644,
        )

        self._mkfile(
            "/etc/passwd",
            """root:x:0:0:root:/root:/bin/bash
user:x:1000:1000:user:/home/user:/bin/bash
research:x:1001:1001:research:/home/research:/bin/bash
backup:x:1002:1002:backup:/var/backups:/usr/sbin/nologin
""",
            owner="root",
            perm=0o644,
        )

        self._mkfile(
            "/etc/sudoers",
            """# Simulated sudo configuration

Defaults env_reset, mail_badpass

user ALL=(root) NOPASSWD: /opt/maintenance/backup.py
""",
            owner="root",
            perm=0o440,
        )

        # ----------------------------------------------------
        # Logs
        # ----------------------------------------------------

        self._mkfile(
            "/var/log/auth.log",
            """Sep 10 08:12:01 lab-server sshd[412]: Accepted password for user
Sep 10 08:13:14 lab-server sudo: user : TTY=pts/0 ; COMMAND=/usr/bin/id
Sep 10 08:15:33 lab-server sudo: user : TTY=pts/0 ; COMMAND=/opt/maintenance/backup.py
""",
            owner="root",
            perm=0o640,
        )

        self._mkfile(
            "/var/log/maintenance.log",
            """[INFO] Backup service initialized
[INFO] Legacy maintenance configuration loaded
[INFO] Backup script: /opt/maintenance/backup.py
""",
            owner="root",
            perm=0o640,
        )

        # ----------------------------------------------------
        # Backup directory
        # ----------------------------------------------------

        self._mkfile(
            "/var/backups/README.txt",
            """Automated backups are stored here.

Do not modify files in this directory manually.
""",
            owner="root",
            perm=0o644,
        )

        # ----------------------------------------------------
        # Existing system binaries
        # ----------------------------------------------------

        self._mkfile(
            "/usr/bin/tar",
            "",
            owner="root",
            perm=0o755,
        )

        self._mkfile(
            "/usr/bin/python3",
            "",
            owner="root",
            perm=0o755,
        )

        self._mkfile(
            "/bin/sh",
            "",
            owner="root",
            perm=0o755,
        )

        # ----------------------------------------------------
        # Root files
        # ----------------------------------------------------

        self._mkfile(
            "/root/root.txt",
            "FORGOTTEN{root_maintenance_complete_91af}\n",
            owner="root",
            perm=0o600,
        )

        self._mkfile(
            "/root/README.txt",
            """Congratulations.

You successfully obtained root access through the vulnerable
maintenance backup process.

The intended vulnerability was PATH Hijacking.
""",
            owner="root",
            perm=0o600,
        )

        # ----------------------------------------------------
        # Temporary debug file
        # ----------------------------------------------------

        self._mkfile(
            "/tmp/debug.log",
            """[DEBUG] Temporary directory initialized.
""",
            owner="root",
            perm=0o644,
        )

    # --------------------------------------------------------
    # Path handling
    # --------------------------------------------------------

    @staticmethod
    def _split(path: str) -> List[str]:
        return [
            part
            for part in path.strip("/").split("/")
            if part
        ]

    def normalize(self, path: str) -> str:
        if not path:
            return self.cwd

        if path.startswith("/"):
            parts: List[str] = []
        else:
            parts = self._split(self.cwd)

        for part in path.split("/"):
            if not part or part == ".":
                continue

            if part == "..":
                if parts:
                    parts.pop()
            else:
                parts.append(part)

        return "/" + "/".join(parts)

    def resolve(self, path: str) -> Optional[Node]:
        normalized = self.normalize(path)

        if normalized == "/":
            return self.root

        current = self.root

        for part in self._split(normalized):
            if current.node_type != "dir":
                return None

            if part not in current.children:
                return None

            current = current.children[part]

        return current

    def parent_and_name(
        self,
        path: str,
    ) -> tuple[Optional[Node], str]:
        normalized = self.normalize(path)
        parts = self._split(normalized)

        if not parts:
            return None, ""

        name = parts[-1]
        parent_path = "/" + "/".join(parts[:-1])

        if parent_path == "":
            parent_path = "/"

        return self.resolve(parent_path), name


fs = VirtualFS()


# ============================================================
# Utility
# ============================================================

def print_prompt() -> str:
    if fs.user == "root":
        return f"root@lab-server:{fs.cwd}# "

    return f"user@lab-server:{fs.cwd}$ "


def format_permissions(node: Node) -> str:
    if node.node_type == "dir":
        prefix = "d"
    else:
        prefix = "-"

    bits = [
        0o400,
        0o200,
        0o100,
        0o040,
        0o020,
        0o010,
        0o004,
        0o002,
        0o001,
    ]

    chars = ["r", "w", "x", "r", "w", "x", "r", "w", "x"]

    result = prefix

    for bit, char in zip(bits, chars):
        result += char if node.perm & bit else "-"

    return result


def is_root() -> bool:
    return fs.user == "root" or STATE["root"]


# ============================================================
# Command: pwd
# ============================================================

def cmd_pwd(args: List[str]) -> None:
    print(fs.cwd)


# ============================================================
# Command: ls
# ============================================================

def cmd_ls(args: List[str]) -> None:
    show_all = False
    long_format = False
    path = fs.cwd

    for arg in args:
        if arg == "--":
            continue

        if arg.startswith("-") and arg != "-":
            if "a" in arg:
                show_all = True

            if "l" in arg:
                long_format = True

            continue

        path = arg

    node = fs.resolve(path)

    if node is None:
        print(f"ls: cannot access '{path}': No such file or directory")
        return

    if node.node_type != "dir":
        if long_format:
            print(
                f"{format_permissions(node)} "
                f"{node.owner:<8} "
                f"{node.name}"
            )
        else:
            print(node.name)

        return

    entries = list(node.children.values())

    if not show_all:
        entries = [
            entry
            for entry in entries
            if not entry.name.startswith(".")
        ]

    if not entries:
        return

    if long_format:
        for entry in entries:
            print(
                f"{format_permissions(entry)} "
                f"{entry.owner:<8} "
                f"{entry.name}"
            )
    else:
        print("  ".join(entry.name for entry in entries))


# ============================================================
# Command: cd
# ============================================================

def cmd_cd(args: List[str]) -> None:
    if not args:
        fs.cwd = "/home/user"
        return

    path = fs.normalize(args[0])
    node = fs.resolve(path)

    if node is None:
        print(f"bash: cd: {args[0]}: No such file or directory")
        return

    if node.node_type != "dir":
        print(f"bash: cd: {args[0]}: Not a directory")
        return

    # Root directory is inaccessible until root is obtained.
    if path.startswith("/root") and not is_root():
        print(f"bash: cd: {args[0]}: Permission denied")
        return

    fs.cwd = path


# ============================================================
# Command: cat
# ============================================================

def cmd_cat(args: List[str]) -> None:
    if not args:
        print("cat: missing operand")
        return

    for path in args:
        node = fs.resolve(path)

        if node is None:
            print(f"cat: {path}: No such file or directory")
            continue

        if node.node_type == "dir":
            print(f"cat: {path}: Is a directory")
            continue

        if path.startswith("/root") and not is_root():
            print(f"cat: {path}: Permission denied")
            continue

        print(node.content)

        if fs.normalize(path) == "/home/user/user.txt":
            STATE["found_backup"] = True


# ============================================================
# Recursive filesystem traversal
# ============================================================

def walk(
    node: Node,
    current_path: str,
):
    yield current_path, node

    if node.node_type != "dir":
        return

    for name, child in node.children.items():
        if current_path == "/":
            child_path = f"/{name}"
        else:
            child_path = f"{current_path}/{name}"

        yield from walk(child, child_path)


# ============================================================
# Command: find
# ============================================================

def cmd_find(args: List[str]) -> None:
    if not args:
        print("find: missing path")
        return

    search_path = args[0]
    name_filter: Optional[str] = None

    index = 1

    while index < len(args):
        arg = args[index]

        if arg == "-name" and index + 1 < len(args):
            name_filter = args[index + 1]
            index += 2
            continue

        index += 1

    root = fs.resolve(search_path)

    if root is None:
        print(
            f"find: '{search_path}': "
            "No such file or directory"
        )
        return

    normalized_root = fs.normalize(search_path)

    for path, node in walk(root, normalized_root):
        if path == normalized_root:
            continue

        if name_filter is not None:
            if node.name != name_filter:
                continue

        if path.startswith("/root") and not is_root():
            continue

        print(path)


# ============================================================
# Command: grep
# ============================================================

def cmd_grep(args: List[str]) -> None:
    if len(args) < 2:
        print("Usage: grep <pattern> <file>")
        return

    pattern = args[0]

    for path in args[1:]:
        node = fs.resolve(path)

        if node is None:
            print(f"grep: {path}: No such file or directory")
            continue

        if node.node_type == "dir":
            print(f"grep: {path}: Is a directory")
            continue

        if path.startswith("/root") and not is_root():
            print(f"grep: {path}: Permission denied")
            continue

        lines = node.content.splitlines()

        for line in lines:
            if pattern in line:
                print(line)


# ============================================================
# Command: whoami
# ============================================================

def cmd_whoami(args: List[str]) -> None:
    print(fs.user)


# ============================================================
# Command: id
# ============================================================

def cmd_id(args: List[str]) -> None:
    if fs.user == "root":
        print(
            "uid=0(root) gid=0(root) "
            "groups=0(root)"
        )
    else:
        print(
            "uid=1000(user) gid=1000(user) "
            "groups=1000(user)"
        )


# ============================================================
# Command: hostname
# ============================================================

def cmd_hostname(args: List[str]) -> None:
    print("lab-server")


# ============================================================
# Command: env
# ============================================================

def cmd_env(args: List[str]) -> None:
    print(f"PATH={STATE['path']}")
    print("USER=" + fs.user)
    print("HOME=" + ("/root" if is_root() else "/home/user"))
    print("SHELL=/bin/bash")


# ============================================================
# Command: echo
# ============================================================

def cmd_echo(args: List[str]) -> None:
    text = " ".join(args)

    text = text.replace(
        "$PATH",
        STATE["path"],
    )

    text = text.replace(
        "${PATH}",
        STATE["path"],
    )

    text = text.replace(
        "$USER",
        fs.user,
    )

    print(text)


# ============================================================
# Command: which
# ============================================================

def cmd_which(args: List[str]) -> None:
    if not args:
        print("which: missing argument")
        return

    command = args[0]

    if command == "tar":
        path_entries = STATE["path"].split(":")

        for directory in path_entries:
            candidate = (
                directory.rstrip("/")
                + "/"
                + command
            )

            node = fs.resolve(candidate)

            if node is not None and node.node_type == "file":
                if node.perm & 0o111:
                    print(candidate)
                    return

        print(f"which: no {command} in ({STATE['path']})")
        return

    if command in ("python", "python3"):
        for directory in STATE["path"].split(":"):
            candidate = (
                directory.rstrip("/")
                + "/"
                + command
            )

            node = fs.resolve(candidate)

            if node is not None:
                print(candidate)
                return

        if command == "python":
            print("/usr/bin/python3")
            return

    print(f"which: no {command} in ({STATE['path']})")


# ============================================================
# Command: export
# ============================================================

def cmd_export(args: List[str]) -> None:
    if not args:
        print(f"PATH={STATE['path']}")
        return

    for assignment in args:
        if "=" not in assignment:
            print(
                f"export: '{assignment}': "
                "not a valid identifier"
            )
            continue

        key, value = assignment.split("=", 1)

        if key == "PATH":
            STATE["path"] = value
            print(f"PATH={STATE['path']}")
        else:
            print(f"{key}={value}")


# ============================================================
# Command: touch
# ============================================================

def cmd_touch(args: List[str]) -> None:
    if not args:
        print("touch: missing file operand")
        return

    for path in args:
        normalized = fs.normalize(path)

        # For this CTF, fake tar creation is intentionally
        # limited to /tmp.
        if not normalized.startswith("/tmp/"):
            print(
                f"touch: cannot touch '{path}': "
                "Permission denied"
            )
            continue

        existing = fs.resolve(normalized)

        if existing is not None:
            print(f"touch: '{path}' already exists")
            continue

        parent, name = fs.parent_and_name(normalized)

        if parent is None or parent.node_type != "dir":
            print(
                f"touch: cannot touch '{path}': "
                "No such file or directory"
            )
            continue

        if fs.user != "user" and fs.user != "root":
            print(
                f"touch: cannot touch '{path}': "
                "Permission denied"
            )
            continue

        new_file = Node(
            name=name,
            node_type="file",
            content="",
            owner=fs.user,
            perm=0o644,
        )

        parent.children[name] = new_file

        if normalized == "/tmp/tar":
            STATE["created_fake_tar"] = True
            print("[+] Created /tmp/tar")
            print("[*] The file is not executable yet.")
        else:
            print(f"[+] Created {normalized}")


# ============================================================
# Command: chmod
# ============================================================

def cmd_chmod(args: List[str]) -> None:
    if len(args) < 2:
        print("chmod: missing operand")
        return

    mode = args[0]
    paths = args[1:]

    # Support common forms such as:
    # chmod +x file
    # chmod 755 file

    for path in paths:
        node = fs.resolve(path)

        if node is None:
            print(
                f"chmod: cannot access '{path}': "
                "No such file or directory"
            )
            continue

        if node.owner != fs.user and not is_root():
            print(
                f"chmod: changing permissions of '{path}': "
                "Operation not permitted"
            )
            continue

        if mode == "+x":
            node.perm |= 0o111

        elif mode == "-x":
            node.perm &= ~0o111

        elif mode.isdigit():
            try:
                node.perm = int(mode, 8)
            except ValueError:
                print(f"chmod: invalid mode: '{mode}'")
                continue

        else:
            print(f"chmod: invalid mode: '{mode}'")
            continue

        print(
            f"Mode of '{path}' changed to "
            f"{node.perm:03o}"
        )


# ============================================================
# Command: python
# ============================================================

def cmd_python(args: List[str]) -> None:
    print(
        "Python interpreter is simulated in this CTF."
    )

    if args:
        print(
            "[*] Python commands are not executed "
            "on the host system."
        )

    print(
        "[*] No privilege escalation is possible "
        "through Python."
    )


# ============================================================
# Command: sudo
# ============================================================

def cmd_sudo(args: List[str]) -> None:
    if not args:
        print(
            "usage: sudo -l | "
            "sudo /opt/maintenance/backup.py"
        )
        return

    # --------------------------------------------------------
    # sudo -l
    # --------------------------------------------------------

    if args[0] == "-l":
        STATE["checked_sudo"] = True

        print(
            "Matching Defaults entries for user on "
            "lab-server:"
        )
        print(
            "    env_reset, mail_badpass"
        )
        print()
        print(
            "User user may run the following commands "
            "on lab-server:"
        )
        print(
            "    (root) NOPASSWD: "
            "/opt/maintenance/backup.py"
        )

        return

    # --------------------------------------------------------
    # sudo backup.py
    # --------------------------------------------------------

    command = args[0]

    if command != "/opt/maintenance/backup.py":
        print(
            f"sudo: {command}: "
            "command not allowed"
        )
        return

    if fs.user == "root":
        print("[*] Already running as root.")
        return

    if not STATE["checked_sudo"]:
        print(
            "sudo: permission denied"
        )
        print(
            "[*] Investigate sudo privileges first."
        )
        return

    cmd_backup([])


# ============================================================
# Vulnerable backup script
# ============================================================

def cmd_backup(args: Optional[List[str]] = None) -> None:
    args = args or []

    if fs.user != "user":
        print(
            "[!] Backup script can only be executed "
            "by user."
        )
        return

    # --------------------------------------------------------
    # Locate tar according to PATH
    # --------------------------------------------------------

    path_entries = STATE["path"].split(":")

    tar_node: Optional[Node] = None
    tar_path: Optional[str] = None

    for directory in path_entries:
        candidate = (
            directory.rstrip("/")
            + "/tar"
        )

        node = fs.resolve(candidate)

        if node is not None and node.node_type == "file":
            tar_node = node
            tar_path = candidate
            break

    if tar_node is None:
        print(
            "[!] tar could not be resolved from PATH."
        )
        return

    # --------------------------------------------------------
    # Intended vulnerability:
    #
    # /tmp/tar exists
    # /tmp/tar is executable
    # /tmp comes before /usr/bin
    # --------------------------------------------------------

    if tar_path != "/tmp/tar":
        print(
            "[*] Starting backup..."
        )
        print(
            "[*] tar resolved to "
            f"{tar_path}"
        )
        print(
            "[!] No PATH hijacking detected."
        )
        print(
            "[+] Backup complete."
        )
        return

    if not STATE["created_fake_tar"]:
        print(
            "[!] /tmp/tar was not created."
        )
        return

    if not (tar_node.perm & 0o111):
        print(
            "[!] /tmp/tar is not executable."
        )
        print(
            "[*] Try: chmod +x /tmp/tar"
        )
        return

    if "/tmp" not in path_entries:
        print(
            "[!] /tmp is not present in PATH."
        )
        return

    if "/usr/bin" in path_entries:
        tmp_index = path_entries.index("/tmp")
        usr_index = path_entries.index("/usr/bin")

        if tmp_index > usr_index:
            print(
                "[!] /tmp appears after /usr/bin."
            )
            return

    # --------------------------------------------------------
    # Exploit successful
    # --------------------------------------------------------

    print("[*] Starting backup...")
    print("[*] Executing tar from PATH...")
    print("[+] /tmp/tar was executed.")
    print("[+] Privilege escalation successful!")

    STATE["executed_exploit"] = True
    STATE["root"] = True

    fs.user = "root"


# ============================================================
# Command: status
# ============================================================

def cmd_status(args: List[str]) -> None:
    print()
    print("=== CTF STATUS ===")
    print()

    print(
        f"User access : "
        f"{'COMPLETE' if STATE['found_backup'] else 'NOT FOUND'}"
    )

    print(
        f"Sudo checked: "
        f"{'YES' if STATE['checked_sudo'] else 'NO'}"
    )

    print(
        f"Fake tar    : "
        f"{'CREATED' if STATE['created_fake_tar'] else 'NO'}"
    )

    print(
        f"Root access : "
        f"{'COMPLETE' if STATE['root'] else 'NO'}"
    )

    print(
        f"PATH        : {STATE['path']}"
    )

    print()


# ============================================================
# Command: hint
# ============================================================

def cmd_hint(args: List[str]) -> None:
    print()

    if not STATE["checked_sudo"]:
        print(
            "[HINT] Check your sudo privileges."
        )

    elif not STATE["created_fake_tar"]:
        print(
            "[HINT] The backup script calls tar."
        )
        print(
            "[HINT] Investigate how tar is resolved."
        )
        print(
            "[HINT] Can you place your own executable "
            "named 'tar' somewhere earlier in PATH?"
        )

    elif not (fs.resolve("/tmp/tar").perm & 0o111):
        print(
            "[HINT] /tmp/tar exists but is not executable."
        )

    elif "/tmp" not in STATE["path"].split(":"):
        print(
            "[HINT] /tmp needs to be included in PATH."
        )

    elif STATE["path"].split(":").index("/tmp") > (
        STATE["path"].split(":").index("/usr/bin")
        if "/usr/bin" in STATE["path"].split(":")
        else 999
    ):
        print(
            "[HINT] PATH is searched from left to right."
        )
        print(
            "[HINT] Put /tmp before /usr/bin."
        )

    elif not STATE["root"]:
        print(
            "[HINT] Run the maintenance backup "
            "script through sudo."
        )

    else:
        print(
            "[+] No hints needed. You are root."
        )

    print()


# ============================================================
# Command: clear
# ============================================================

def cmd_clear(args: List[str]) -> None:
    print("\033[2J\033[H", end="")


# ============================================================
# Command: help
# ============================================================

def cmd_help(args: List[str]) -> None:
    print()
    print("Available commands:")
    print()
    print("  pwd")
    print("  ls [options] [path]")
    print("  cd <path>")
    print("  cat <file>")
    print("  find <path> [-name <name>]")
    print("  grep <pattern> <file>")
    print("  id")
    print("  whoami")
    print("  hostname")
    print("  env")
    print("  echo <text>")
    print("  which <command>")
    print("  export PATH=<path>")
    print("  touch <file>")
    print("  chmod <mode> <file>")
    print("  sudo -l")
    print("  sudo /opt/maintenance/backup.py")
    print("  python")
    print("  python3")
    print("  status")
    print("  hint")
    print("  clear")
    print("  help")
    print("  exit")
    print()


# ============================================================
# Command: exit
# ============================================================

def cmd_exit(args: List[str]) -> bool:
    return True


# ============================================================
# Command table
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
    "echo": cmd_echo,
    "which": cmd_which,
    "export": cmd_export,
    "touch": cmd_touch,
    "chmod": cmd_chmod,
    "sudo": cmd_sudo,
    "python": cmd_python,
    "python3": cmd_python,
    "status": cmd_status,
    "hint": cmd_hint,
    "clear": cmd_clear,
    "help": cmd_help,
}


# ============================================================
# Command execution
# ============================================================

def execute_command(command_line: str) -> bool:
    command_line = command_line.strip()

    if not command_line:
        return False

    try:
        args = shlex.split(command_line)
    except ValueError as exc:
        print(f"bash: syntax error: {exc}")
        return False

    if not args:
        return False

    command = args[0]
    command_args = args[1:]

    if command == "exit":
        return True

    if command not in COMMANDS:
        print(
            f"bash: {command}: "
            "command not found"
        )
        return False

    try:
        COMMANDS[command](command_args)
    except Exception as exc:
        print(
            f"[internal error] "
            f"{type(exc).__name__}: {exc}"
        )

    # --------------------------------------------------------
    # Root flag detection
    # --------------------------------------------------------

    if STATE["root"] and not STATE.get("_root_message_shown"):
        STATE["_root_message_shown"] = True

        print()
        print(
            "[+] You now have root privileges."
        )
        print(
            "[+] Try: whoami"
        )
        print(
            "[+] Then investigate /root."
        )
        print()

    return False


# ============================================================
# Banner
# ============================================================

def print_banner() -> None:
    print()
    print(
        "╔══════════════════════════════════════════════════════════╗"
    )
    print(
        "║                  THE FORGOTTEN SERVER                   ║"
    )
    print(
        "║                    Linux CTF - Easy                     ║"
    )
    print(
        "╚══════════════════════════════════════════════════════════╝"
    )
    print()
    print(
        "A forgotten internal research server has been found."
    )
    print(
        "Investigate the system and obtain the flags."
    )
    print()
    print("Targets:")
    print("  - user.txt")
    print("  - root.txt")
    print()
    print(
        "Type 'help' for available commands."
    )
    print()


# ============================================================
# Main
# ============================================================

def main() -> None:
    print_banner()

    session = PromptSession()

    with patch_stdout():
        while True:
            try:
                command_line = session.prompt(
                    print_prompt()
                )

            except (EOFError, KeyboardInterrupt):
                print()
                break

            should_exit = execute_command(command_line)

            if should_exit:
                print("Connection closed.")
                break

            # ------------------------------------------------
            # Win condition
            # ------------------------------------------------

            if STATE["root"]:
                root_flag = fs.resolve("/root/root.txt")

                if root_flag is not None:
                    # Don't automatically reveal the flag.
                    # Player must read root.txt manually.
                    pass


if __name__ == "__main__":
    main()