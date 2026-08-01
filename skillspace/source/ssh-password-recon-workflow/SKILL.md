---
name: ssh-password-recon-workflow
description: "Use when performing remote reconnaissance or command execution on Linux hosts via SSH with password authentication, especially in restricted environments where sshpass is unavailable and pexpect suffers from output-buffer mixing. Provides a paramiko-based workflow that executes commands individually and isolates outputs to avoid file-reading token limits. NOT for: key-based SSH access, local host analysis, or interactive TTY exploitation requiring persistent shell sessions."
category: general
---

When password-based SSH reconnaissance is required and `sshpass` is unavailable or cannot be installed, use Python `paramiko` instead of `pexpect` to avoid interactive buffer mixing.

1. Connect with `paramiko.SSHClient()`, set `AutoAddPolicy`, and authenticate with `connect(hostname, username=..., password=..., timeout=30)`.
2. Run each recon command via a separate `exec_command()` call. Do not send multiple commands in one long interactive session.
3. Write each command's stdout to its own local file immediately (e.g., `/tmp/recon_cmd_1.txt`). **Do not** concatenate all outputs into a single large file.
4. Inspect results with `Grep` or Bash text-processing tools (`head`, `tail`, `grep`, `awk`). Avoid using `Read` on very large files because it may truncate or refuse even when `offset`/`limit` are provided.
5. Close the client when finished.

Example:
python
import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.184', username='Eliza', password='Beth2026', timeout=30)

cmds = [
    "uname -a && cat /etc/VERSION 2>/dev/null || cat /etc/os-release 2>/dev/null",
    "ps aux --sort=-rss | head -50",
    "netstat -tlnp 2>/dev/null || ss -tlnp",
    "find /run /tmp /var/run -name '*.socket' -o -name '*.sock' 2>/dev/null | head -20",
    "ls -la /usr/syno/etc/packages/ 2>/dev/null | awk '{print $NF}'",
    "cat /etc/group | grep administrators",
    "synopkg list 2>/dev/null || ls /var/packages/",
    "id"
]

for i, cmd in enumerate(cmds, 1):
    _, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    with open(f'/tmp/recon_cmd_{i}.txt', 'w') as f:
        f.write(out)
        if err:
            f.write('\n[STDERR]\n' + err)

client.close()

