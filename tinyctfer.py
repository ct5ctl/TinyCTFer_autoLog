"""
TinyCTFer - A 100-line "Baby Runtime" for Intent Engineering

Authors: l3yx, m09ic

Philosophy: "Intent is All You Need" 

Meta-Tooling Innovation:
Traditional: Agent → Tool A → Parse → Tool B → Parse... (context pollution)
Ours:  Agent Intent → Write Python Code → Execute → Final Result 

Result: Top 4 in Tencent Cloud Hackathon (238 teams), only ~1500 RMB tokens (kimi k2, not deepseek)

Components: Claude Code + AI-Friendly Sandbox ( Python Executor MCP + Meta-Tooling + VNC)

References:
- https://wiki.chainreactors.red/blog/2025/12/01/intent_is_all_you_need/
- https://wiki.chainreactors.red/blog/2025/12/02/intent_engineering_01/
"""

import os
import argparse
from pathlib import Path
import docker
from docker.models.containers import Container
from docker.errors import ImageNotFound

# Script directory for mounting claude_code configuration into container
SCRIPT_DIR = Path(__file__).resolve().parent
print(SCRIPT_DIR)

class Ctfer:
    """CTF Solver Runtime - Provide AI maximum freedom within safe container boundary"""
    def __init__(self, vnc_port, workspace):
        # Sandbox: Ubuntu desktop + Claude Code + Python Executor MCP + Toolset + Security tools
        self.image = "l3yx/sandbox:latest"
        self.volumes = [
            f"{SCRIPT_DIR/'claude_code'}:/opt/claude_code:ro",  # Claude config (ro)
            f"{workspace}:/home/ubuntu/Workspace",  # AI's workspace (rw)
            f"{SCRIPT_DIR}/entrypoint.sh:/entrypoint.sh:ro",  # Claude config (ro)
        ]
        self.environment = {  # Anthropic API credentials
            "ANTHROPIC_BASE_URL": os.getenv("ANTHROPIC_BASE_URL"),
            "ANTHROPIC_AUTH_TOKEN": os.getenv("ANTHROPIC_AUTH_TOKEN"),
            "ANTHROPIC_MODEL": os.getenv("ANTHROPIC_MODEL"),
            "NO_CODESERVER": "true",
            # hint for logger where workspace lives (inside container)
            "WORKSPACE_DIR": "/home/ubuntu/Workspace",
        }
        self.ports = {f"{vnc_port}":"5901"}  # VNC for human observation
        try:
            self.docker_client = docker.DockerClient()
        except Exception as e:
            print(f"[-] Failed to connect to Docker: {e}")
            print("[-] Please ensure Docker is running and you have permission to access it.")
            print("[-] Try: sudo usermod -aG docker $USER (then log out and back in)")
            raise
        self.container = None
        try:
            self.docker_client.images.get(self.image)
        except ImageNotFound:
            print(f"[-] Docker image '{self.image}' not found. Please pull it first.")
            exit(1)
        except Exception as e:
            print(f"[-] Failed to access Docker: {e}")
            raise
        
        # Check and clean up containers using the same port
        self._cleanup_port_conflicts(vnc_port)
        
        try:
            self.container:Container = self.docker_client.containers.run(
                image=self.image, volumes=self.volumes, environment=self.environment,
                ports=self.ports, detach=True, remove=False,
            )
            check = self.container.exec_run("bash -c 'id && pwd'")
            print(check.output)
        except Exception as e:
            error_msg = str(e)
            if "port is already allocated" in error_msg or "address already in use" in error_msg.lower():
                print(f"[!] Port {vnc_port} is already in use. Attempting to clean up conflicting containers...")
                self._cleanup_port_conflicts(vnc_port, force=True)
                # Retry once after cleanup
                try:
                    self.container:Container = self.docker_client.containers.run(
                        image=self.image, volumes=self.volumes, environment=self.environment,
                        ports=self.ports, detach=True, remove=False,
                    )
                    check = self.container.exec_run("bash -c 'id && pwd'")
                    print(check.output)
                    print(f"[+] Container started successfully after cleanup")
                except Exception as retry_e:
                    print(f"[-] Failed to start container after cleanup: {retry_e}")
                    print(f"[-] Please manually stop the container using port {vnc_port} or use a different --vnc-port")
                    print(f"[-] You can check with: docker ps | grep :{vnc_port}")
                    raise
            else:
                print(f"[-] Failed to start container: {e}")
                raise
    
    def _cleanup_port_conflicts(self, port, force=False):
        """Stop containers that are using the specified port."""
        try:
            containers = self.docker_client.containers.list(all=True)
            for container in containers:
                try:
                    port_mappings = container.attrs.get('NetworkSettings', {}).get('Ports', {})
                    for container_port, host_bindings in port_mappings.items():
                        if host_bindings:
                            for binding in host_bindings:
                                if binding.get('HostPort') == str(port):
                                    print(f"[!] Found container {container.id[:12]} using port {port}")
                                    if force:
                                        print(f"[!] Stopping container {container.id[:12]}...")
                                        container.stop(timeout=5)
                                        container.remove()
                                        print(f"[+] Container {container.id[:12]} stopped and removed")
                                    return
                except Exception:
                    # Skip containers that can't be inspected
                    continue
        except Exception as e:
            if force:
                print(f"[!] Warning: Could not check for port conflicts: {e}")

    def cleanup(self):
        if hasattr(self, 'container') and self.container:
            try:
                self.container.stop(timeout=5)
            except Exception:
                pass

    def __del__(self):
        try:
            self.cleanup()
        except Exception:
            pass

if __name__ == "__main__":
    # Main Entry Point: The 100-line Baby Runtime in Action
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
    print(f"[+] 开始解题, 可以打开 {workspace} 查看解题步骤")
    print(f"[+] 输入提示词：{task}")

    # Initialize structured log inside sandbox before starting Claude
    init_script = f"""import os
import sys

# Ensure logs directory exists even if toolset import fails
workspace_dir = os.getenv("WORKSPACE_DIR", "/home/ubuntu/Workspace")
logs_dir = os.path.join(workspace_dir, "logs")
print(f"[LOGGER] Creating logs directory: {{logs_dir}}", file=sys.stderr)
os.makedirs(logs_dir, exist_ok=True)

# Verify directory was created
if os.path.exists(logs_dir):
    print(f"[LOGGER] Logs directory created successfully: {{logs_dir}}", file=sys.stderr)
else:
    print(f"[LOGGER] ERROR: Failed to create logs directory: {{logs_dir}}", file=sys.stderr)
    sys.exit(1)

# Debug: setup debug logging first
debug_path = os.path.join(workspace_dir, ".cursor", "debug.log")
os.makedirs(os.path.dirname(debug_path), exist_ok=True)
import json
try:
    with open(debug_path, "a") as f:
        f.write(json.dumps({{"sessionId":"debug-session","runId":"run1","hypothesisId":"INIT","location":"tinyctfer.py:init_script","message":"init script start","data":{{"python_path":sys.path,"workspace_dir":workspace_dir}}}}) + "\\n")
except: pass

# Try to import toolset and initialize logger
try:
    import toolset
    import json
    
    # Debug: write toolset info
    try:
        with open(debug_path, "a") as f:
            toolset_attrs = [attr for attr in dir(toolset) if not attr.startswith('_')]
            f.write(json.dumps({{"sessionId":"debug-session","runId":"run1","hypothesisId":"INIT","location":"tinyctfer.py:init_script","message":"toolset imported","data":{{"toolset_attrs":toolset_attrs,"has_logger_attr":hasattr(toolset, 'logger'),"toolset_file":getattr(toolset, '__file__', 'NO_FILE')}}}}) + "\\n")
    except Exception as debug_e:
        print(f"[DEBUG] Failed to write debug log: {{debug_e}}", file=sys.stderr)
    
    # Check if logger exists
    if hasattr(toolset, 'logger'):
        logger_obj = toolset.logger
        if logger_obj is not None:
            logger_obj.set_initial_prompt({task!r})
            log_path = logger_obj.get_filepath()
            print(f"[LOGGER] Initialized, log file: {{log_path}}", file=sys.stderr)
            # Debug: confirm success
            try:
                with open(debug_path, "a") as f:
                    f.write(json.dumps({{"sessionId":"debug-session","runId":"run1","hypothesisId":"INIT","location":"tinyctfer.py:init_script","message":"logger initialized","data":{{"log_path":log_path}}}}) + "\\n")
            except: pass
        else:
            print(f"[LOGGER] Warning: toolset.logger is None", file=sys.stderr)
            try:
                with open(debug_path, "a") as f:
                    f.write(json.dumps({{"sessionId":"debug-session","runId":"run1","hypothesisId":"INIT","location":"tinyctfer.py:init_script","message":"logger is None","data":{{}}}}) + "\\n")
            except: pass
    else:
        print(f"[LOGGER] Warning: toolset has no 'logger' attribute", file=sys.stderr)
        toolset_attrs = [attr for attr in dir(toolset) if not attr.startswith('_')]
        print(f"[LOGGER] toolset attributes: {{toolset_attrs}}", file=sys.stderr)
        try:
            with open(debug_path, "a") as f:
                f.write(json.dumps({{"sessionId":"debug-session","runId":"run1","hypothesisId":"INIT","location":"tinyctfer.py:init_script","message":"logger attribute missing","data":{{"toolset_attrs":toolset_attrs,"toolset_file":getattr(toolset, '__file__', 'NO_FILE')}}}}) + "\\n")
        except: pass
except Exception as e:
    print(f"[LOGGER] Warning: Failed to initialize logger: {{e}}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    # Debug: log exception
    try:
        with open(debug_path, "a") as f:
            f.write(json.dumps({{"sessionId":"debug-session","runId":"run1","hypothesisId":"INIT","location":"tinyctfer.py:init_script","message":"exception during init","data":{{"error":str(e),"error_type":type(e).__name__,"traceback":traceback.format_exc()}}}}) + "\\n")
    except: pass
    # Directory already created above as fallback
"""
    # Try python3 first, fallback to python
    logger_init_success = False
    for python_cmd in ["python3", "python"]:
        result = ctfer.container.exec_run(
            [python_cmd, "-c", init_script],
            workdir="/home/ubuntu/Workspace",
            environment={"WORKSPACE_DIR": "/home/ubuntu/Workspace"},  # Explicitly set env
        )
        output = result.output.decode('utf-8', errors='replace')
        if result.exit_code == 0:
            if output:
                print(f"[+] Logger init output: {output}")
            logger_init_success = True
            break
        else:
            print(f"[!] Logger init failed with {python_cmd}: {output}")
            if python_cmd == "python":
                # Both failed, show error
                print("[!] Failed to initialize logger with both python3 and python")

    print(ctfer.container.logs().decode('utf-8'))
    #res = ctfer.container.exec_run(["claude", "--dangerously-skip-permissions", "--print", task], workdir="/home/ubuntu/Workspace")
    res = ctfer.container.exec_run(["claude", "--dangerously-skip-permissions", "--print", task], workdir="/opt/claude_code")

    # Best-effort: let agent log final report via logger tools; nothing to do here explicitly
    ctfer.cleanup()
    print("[+] 结束运行")
    print(bytes.decode(res.output))
