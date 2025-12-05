import os
import argparse
from pathlib import Path
import docker
from docker.models.containers import Container
from docker.errors import ImageNotFound

SCRIPT_DIR = Path(__file__).resolve().parent

class Ctfer:
    def __init__(self, vnc_port, workspace):
        self.image = "l3yx/sandbox:latest"
        self.volumes = [
            f"{SCRIPT_DIR/'claude_code'}:/opt/claude_code:ro",
            f"{workspace}:/home/ubuntu/Workspace"
        ]
        self.environment = {
            "ANTHROPIC_BASE_URL": os.getenv("ANTHROPIC_BASE_URL"),
            "ANTHROPIC_AUTH_TOKEN": os.getenv("ANTHROPIC_AUTH_TOKEN"),
            "ANTHROPIC_MODEL": os.getenv("ANTHROPIC_MODEL"),
            "NO_CODESERVER": "true"
        }
        self.ports = {
            f"{vnc_port}":"5901",
        }
        self.docker_client = docker.DockerClient()
        self.container = None
        try:
            self.docker_client.images.get(self.image)
        except ImageNotFound:
            print(f"[-] Docker image '{self.image}' not found. Please pull it first.")
            exit(1)
        self.container:Container = self.docker_client.containers.run(
            image=self.image,
            volumes=self.volumes,
            environment=self.environment,
            ports=self.ports,
            detach=True,
            remove=True
        )

    def __del__(self):
        if  self.container:
            try:
                self.container.stop(timeout=5)
            except Exception as e:
                pass

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
print(f"[+] 可以连接 vnc://127.0.0.1:{vnc_port} 查看可视化界面, 密码123456")
print("[+] 开始解题...")
print(f"[+] 可以打开 {workspace} 查看解题步骤")
res = ctfer.container.exec_run(["claude", "--dangerously-skip-permissions", "--print", task], workdir="/opt/claude_code")
print("[+] 结束运行")
print(bytes.decode(res.output))