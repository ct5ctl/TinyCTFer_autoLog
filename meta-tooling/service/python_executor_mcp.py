import time
import os
import re
import argparse
from typing import Annotated, Optional
from queue import Empty
import nbformat
from jupyter_client import KernelManager
from nbformat import v4 as nbf
from fastmcp import FastMCP

# toolset is available inside the sandbox; logger integration
try:
    import toolset  # type: ignore
except Exception:  # pragma: no cover - defensive import
    toolset = None

class PythonExecutor:
    def __init__(self, path="scripts"):
        self.path = path
        self.sessions = {}
        os.makedirs(self.path, exist_ok=True)

    def _sanitize_filename(self, name):
        name = re.sub(r'[^\w\-.]', '_', name)
        return name

    def _get_unique_filepath(self, session_name):
        sanitized_name = self._sanitize_filename(session_name)
        base_path = os.path.join(self.path, f"{sanitized_name}.ipynb")
        if not os.path.exists(base_path):
            return base_path
        i = 1
        while True:
            new_path = os.path.join(self.path, f"{sanitized_name}_{i}.ipynb")
            if not os.path.exists(new_path):
                return new_path
            i += 1

    def _create_session(self, session_name):
        km = KernelManager(kernel_name='python3')
        km.start_kernel()
        client = km.client()
        client.start_channels()
        try:
            client.wait_for_ready(timeout=3)
        except RuntimeError:
            client.stop_channels()
            km.shutdown_kernel(now=True)
            raise RuntimeError("Kernel did not start in time.")

        filepath = self._get_unique_filepath(session_name)
        notebook = nbf.new_notebook()

        self.sessions[session_name] = {
            'km': km,
            'client': client,
            'notebook': notebook,
            'filepath': filepath,
            'execution_count': 1
        }
        return self.sessions[session_name]
    
    def _format_output(self, output_objects):
        formatted_outputs = []
        for out in output_objects:
            output_type = out.output_type
            if output_type == 'stream':
                formatted_outputs.append({
                    "type": "stream",
                    "name": out.name,
                    "text": out.text
                })
            elif output_type == 'execute_result':
                formatted_outputs.append({
                    "type": "execute_result",
                    "data": dict(out.data),
                    "execution_count": out.execution_count
                })
            elif output_type == 'display_data':
                formatted_outputs.append({
                    "type": "display_data",
                    "data": dict(out.data)
                })
            elif output_type == 'error':
                formatted_outputs.append({
                    "type": "error",
                    "ename": out.ename,
                    "evalue": out.evalue,
                    "traceback": out.traceback
                })   
        return formatted_outputs

    def list_sessions(self):
        return list(self.sessions.keys())

    def execute_code(self, session_name, code, timeout=10):
        if session_name not in self.sessions:
            self._create_session(session_name)
        
        session = self.sessions[session_name]        
        client = session['client']
        km = session['km']
        notebook = session['notebook']
        filepath = session['filepath']
        exec_count = session['execution_count']

        # Inject logging code that runs inside the container's Python environment
        # This code will execute in the Jupyter kernel, where toolset is available
        import json
        code_escaped = json.dumps(code)
        log_code_injection = f"""
# Auto-injected logging code (runs in container's Python environment)
try:
    import toolset
    import sys
    import os
    import json
    
    # Debug: check if logger exists
    has_logger = hasattr(toolset, 'logger')
    logger_value = getattr(toolset, 'logger', None)
    
    # Write debug info to file
    debug_path = os.path.join(os.getenv("WORKSPACE_DIR", "/home/ubuntu/Workspace"), ".cursor", "debug.log")
    os.makedirs(os.path.dirname(debug_path), exist_ok=True)
    try:
        with open(debug_path, "a") as f:
            f.write(json.dumps({{"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"python_executor_mcp.py:injection","message":"code injection executed","data":{{"has_logger":has_logger,"logger_type":str(type(logger_value)) if logger_value else "None","logger_is_none":logger_value is None}}}}) + "\\n")
    except: pass
    
    if has_logger and logger_value is not None:
        code_to_log = json.loads({json.dumps(code_escaped)})
        toolset.logger.log_code(code_to_log)
        # Debug: confirm logging succeeded
        try:
            with open(debug_path, "a") as f:
                f.write(json.dumps({{"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"python_executor_mcp.py:injection","message":"log_code called","data":{{"code_length":len(code_to_log)}}}}) + "\\n")
        except: pass
    else:
        # Debug: logger not available
        try:
            with open(debug_path, "a") as f:
                f.write(json.dumps({{"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"python_executor_mcp.py:injection","message":"logger not available","data":{{"has_logger":has_logger,"logger_value":str(logger_value)}}}}) + "\\n")
        except: pass
except Exception as e:
    # Debug: log exception
    try:
        import os, json
        debug_path = os.path.join(os.getenv("WORKSPACE_DIR", "/home/ubuntu/Workspace"), ".cursor", "debug.log")
        os.makedirs(os.path.dirname(debug_path), exist_ok=True)
        with open(debug_path, "a") as f:
            f.write(json.dumps({{"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"python_executor_mcp.py:injection","message":"logging injection failed","data":{{"error":str(e),"error_type":type(e).__name__}}}}) + "\\n")
    except: pass

"""
        # Prepend logging injection to user code
        code_with_logging = log_code_injection + code

        cell = nbf.new_code_cell(code_with_logging, execution_count=exec_count)
        cell.outputs = []
        notebook.cells.append(cell)
        with open(filepath, 'w', encoding='utf-8') as f:
            nbformat.write(notebook, f)

        msg_id = client.execute(code_with_logging)

        output_objects = []
        start_time = time.time()

        try:
            shell_reply_received = False
            
            while True:
                elapsed = time.time() - start_time
                
                if elapsed > timeout:
                    error_msg = f"Execution timeout after {timeout} seconds. Attempting to interrupt..."
                    output_objects.append(nbf.new_output('display_data', data={'text/plain': f'[SYSTEM] {error_msg}'}))

                    try:
                        km.interrupt_kernel()
                        time.sleep(1)          
                        try: # 清空剩余消息
                            while True:
                                msg = client.get_iopub_msg(timeout=0.1)
                                if msg['parent_header'].get('msg_id') == msg_id:
                                    msg_type = msg['header']['msg_type']
                                    if msg_type == 'status' and msg['content']['execution_state'] == 'idle':
                                        break
                        except Empty:
                            pass
                        
                        interrupt_msg = "Kernel interrupted. Session state preserved."
                        output_objects.append(nbf.new_output('display_data', data={'text/plain': f'[SYSTEM] {interrupt_msg}'}))
                    except Exception as e:
                        interrupt_error = f"Failed to interrupt kernel: {repr(e)}"
                        output_objects.append(nbf.new_output('display_data', data={'text/plain': f'[SYSTEM] {interrupt_error}'}))
                    
                    break
                
                try:
                    msg = client.get_iopub_msg(timeout=0.1)
                    if msg['parent_header'].get('msg_id') != msg_id:
                        continue

                    msg_type = msg['header']['msg_type']
                    content = msg['content']

                    if msg_type == 'status' and content['execution_state'] == 'idle':
                        break # 执行完成，退出循环
                    
                    if msg_type == 'stream':
                        text = content.get('text', '')
                        output_objects.append(nbf.new_output('stream', name=content.get('name', 'stdout'), text=text))
                    elif msg_type == 'execute_result':
                        output_objects.append(nbf.new_output('execute_result', data=content.get('data', {}), execution_count=exec_count))
                    elif msg_type == 'display_data':
                        output_objects.append(nbf.new_output('display_data', data=content.get('data', {})))
                    elif msg_type == 'error':
                        output_objects.append(nbf.new_output('error', ename=content.get('ename', ''), evalue=content.get('evalue', ''), traceback=content.get('traceback', [])))

                except Empty:
                    if not shell_reply_received:
                        try:
                            # 尝试获取 shell 消息，如果成功，说明执行结果已返回
                            client.get_shell_msg(timeout=0.1)
                            shell_reply_received = True
                        except Empty:
                            pass
                    continue
                    
        except Exception as e:
            error_msg = f"Failed to execute code or retrieve output: {repr(e)}"
            output_objects.append(
                nbf.new_output(
                    "display_data",
                    data={"text/plain": f"[SYSTEM] {error_msg}"},
                )
            )

        cell.outputs = output_objects if output_objects else []
        with open(filepath, 'w', encoding='utf-8') as f:
            nbformat.write(notebook, f)

        session['execution_count'] += 1

        formatted = self._format_output(output_objects)

        # Log observations in the container's Python environment
        # Inject code that will run after execution to log observations
        if formatted:
            try:
                import json
                observations_json_str = json.dumps(formatted)
                # Escape the JSON string for embedding in Python code
                observations_json_escaped = json.dumps(observations_json_str)
                
                log_observations_code = f"""
# Auto-injected observation logging (runs in container's Python environment)
try:
    import toolset
    import json
    observations_json = json.loads({observations_json_escaped})
    observations = json.loads(observations_json)
    for item in observations:
        obs_type = "code_output"
        if item.get("type") == "error":
            obs_type = "error"
        
        # Optional planning extraction
        if (
            item.get("type") == "stream"
            and isinstance(item.get("text"), str)
        ):
            text = item["text"].lstrip()
            if text.lower().startswith(("plan:", "planning:")):
                try:
                    if hasattr(toolset, 'logger_tools'):
                        toolset.logger_tools.log_planning(text)
                except Exception:
                    pass
        
        # Log observation
        if hasattr(toolset, 'logger'):
            toolset.logger.log_observation(item, obs_type)
except Exception:
    pass  # Logger not available, continue anyway
"""
                # Execute observation logging in the same session (fire and forget)
                try:
                    # Execute asynchronously without waiting for completion
                    client.execute(log_observations_code)
                    # Give a tiny bit of time for async execution
                    time.sleep(0.05)
                except Exception:
                    pass  # Don't break execution if logging fails
            except Exception:
                pass  # Don't break execution if observation logging setup fails

        return formatted

    def close_session(self, session_name):
        if session_name not in self.sessions:
            return False
        session = self.sessions.pop(session_name)
        session['client'].stop_channels()
        session['km'].shutdown_kernel(now=True)
        return True

    def close_all_sessions(self):
        for session_name in list(self.sessions.keys()):
            self.close_session(session_name)

mcp = FastMCP("Python Executor", include_fastmcp_meta=False)
python_executer = PythonExecutor()

@mcp.tool(output_schema=None)
def execute_code(
    session_name: Annotated[str, "Unique session ID. Same name shares state (vars, imports)."],
    code: Annotated[str, "Python code (multi-line OK). Runs in Jupyter kernel. Supports `%pip install pkg` and `!shell_cmd`."],
    timeout: Annotated[Optional[int], "Max seconds (default: 10). Timeout interrupts but keeps session alive."]
) -> list[dict]:
    """
    Run Python code in a stateful Jupyter kernel.

    - Preserves variables/functions across calls.
    - Supports magic `%pip` and shell `!cmd`.
    - Built-in toolset library allows you to control the browser, command-line terminal, proxy analysis tools, etc. in the sandbox environment. Execute the following code to view help:
    ```
    import toolset
    help(toolset)
    ```
    """
    return python_executer.execute_code(
        session_name=session_name,
        code=code,
        timeout=timeout or 10
    )

@mcp.tool(output_schema=None)
def list_sessions() -> list[str]:
    """Return list of active session names."""
    return python_executer.list_sessions()

@mcp.tool(output_schema=None)
def close_session(session_name: Annotated[str, "Session to close."]) -> bool:
    """Close a session."""
    return python_executer.close_session(session_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument('--host', type=str, default='0.0.0.0')
    args = parser.parse_args()
    mcp.run(transport="streamable-http", host=args.host, port=args.port)