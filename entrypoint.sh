#!/bin/bash
set -e
pwd
id

ls -al ../
source ~/.myrc
sudo chown -R ubuntu:ubuntu /home/ubuntu

export VNC_PORT=5901
export CAIDO_PORT=8080
export CODE_PORT=9090
export BROWSER_PORT=9222
export MCP_PORT=8000

# 启动dbus
# eval $(dbus-launch --sh-syntax)
# echo "export DBUS_SESSION_BUS_ADDRESS=$DBUS_SESSION_BUS_ADDRESS" >> ~/.myrc

# 启动VNC
if [ -z "${NO_VISION}" ]; then
  mkdir -p ~/.vnc && echo 123456 | vncpasswd -f >~/.vnc/passwd && chmod 600 ~/.vnc/passwd
  vncserver $DISPLAY -rfbport $VNC_PORT -geometry 1920x1080 -depth 24 -localhost no -xstartup /usr/bin/startxfce4
fi

# 运行Caido
caido-cli --no-sync --no-open --allow-guests --listen 0.0.0.0:$CAIDO_PORT >/dev/null 2>&1 &
while ! curl -s --head http://localhost:$CAIDO_PORT/ca.crt >/dev/null; do
  sleep 1
done
# 下载Caido证书
CA_CERT_PATH="/usr/local/share/ca-certificates/caido-ca.crt"
echo "Downloading certificate to $CA_CERT_PATH..."
sudo curl -s http://localhost:$CAIDO_PORT/ca.crt -o "$CA_CERT_PATH"
# 将Caido证书添加到NSS数据库(浏览器等)
rm -rf ~/.pki/nssdb
mkdir -p ~/.pki/nssdb
certutil -N -d sql:$HOME/.pki/nssdb --empty-password
certutil -A -n "Testing Root CA" -t "C,," -i $CA_CERT_PATH -d sql:$HOME/.pki/nssdb
# 获取Caido Token
export CAIDO_TOKEN=$(curl -s -X POST \
  -H "Content-Type: application/json" \
  -d '{"query":"mutation LoginAsGuest { loginAsGuest { token { accessToken } } }"}' \
  http://localhost:$CAIDO_PORT/graphql | jq -r '.data.loginAsGuest.token.accessToken')
if [ -z "$CAIDO_TOKEN" ] || [ "$CAIDO_TOKEN" == "null" ]; then
  echo "Failed to get API token from Caido."
  exit 1
fi
# 创建和选择Caido项目
CREATE_PROJECT_RESPONSE=$(curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CAIDO_TOKEN" \
  -d '{"query":"mutation CreateProject { createProject(input: {name: \"sandbox\", temporary: true}) { project { id } } }"}' \
  http://localhost:$CAIDO_PORT/graphql)
PROJECT_ID=$(echo $CREATE_PROJECT_RESPONSE | jq -r '.data.createProject.project.id')
echo "Selecting Caido project..."
curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CAIDO_TOKEN" \
  -d '{"query":"mutation SelectProject { selectProject(id: \"'$PROJECT_ID'\") { currentProject { project { id } } } }"}' \
  http://localhost:$CAIDO_PORT/graphql

# 启动浏览器显示Caido
if [ -z "${NO_VISION}" ]; then
  chrome --no-sandbox --app=http://localhost:$CAIDO_PORT/ --user-data-dir="$HOME/.config/chromium-caido" --test-type --window-position=200,200 --window-size=1200,800 >/dev/null 2>&1 &
fi

# 启动code-server
if [ -z "${NO_CODESERVER}" ]; then
  code-server --disable-workspace-trust --bind-addr 0.0.0.0:${CODE_PORT} --auth none ~/Workspace >/dev/null 2>&1 &
  while ! curl -s --head http://localhost:$CODE_PORT/ >/dev/null; do
    sleep 1
  done

  # 启动浏览器显示code-server
  if [ -z "${NO_VISION}" ]; then
    chrome --no-sandbox --app=http://localhost:$CODE_PORT/ --user-data-dir="$HOME/.config/chromium-code" --test-type --window-position=100,100 --window-size=1200,800 >/dev/null 2>&1 &
  fi
fi

# 启动Playwright浏览器
python3 /opt/service/browser.py --port $BROWSER_PORT >/dev/null 2>&1 &

# 启动Python Executor MCP
python3 /opt/service/python_executor_mcp.py --port $MCP_PORT
