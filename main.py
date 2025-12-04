import os
import argparse
from ctfer import Ctfer

parser = argparse.ArgumentParser(description='CTF Challenge Solver')
parser.add_argument('--ctf', type=str, required=True, help='CTF challenge URL')
parser.add_argument('--vnc-port', type=int, default=5901, help='VNC port (default: 5901)')
parser.add_argument('--workspace', type=str, default="workspace", help='Workspace directory (default: workspace)')

args = parser.parse_args()
ctf = args.ctf
vnc_port = args.vnc_port
workspace = os.path.abspath(args.workspace)


task = f'''
Use the security-ctf-agent: Solve the CTF challenge (obtaining the Flag completes the task, you can end work immediately, don't need to verify the flag's accuracy.)

Challenge Information:
{ctf}

**You don't need to scan ports or IP segments, all IP and ports needed for solving are already listed**
'''.strip()
print("[+] 启动沙盒...")
ctfer = Ctfer(vnc_port, workspace)
print("[+] 等待沙盒环境和mcp服务就绪...")
ctfer.container.exec_run(["bash","wait.sh"], workdir="/opt/claude_code")
print("[+] mcp服务已就绪...")
print(f"[+] 可以连接 vnc://127.0.0.1:{vnc_port} 查看可视化界面")
print("[+] 开始解题...")
res = ctfer.container.exec_run(["claude", "--dangerously-skip-permissions", "--print", task], workdir="/opt/claude_code")
print("[+] 结束运行")
print(bytes.decode(res.output))