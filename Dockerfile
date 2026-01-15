FROM ghcr.io/l3yx/sandbox:latest

# 2. 切换到 root 用户以执行权限修改操作
USER root

# 3. 修复权限：将 /opt/service 的所有权交给 ubuntu 用户
# 这样 /opt/service/python_executor_mcp.py 运行时就能创建 scripts 文件夹了
RUN chown -R ubuntu:ubuntu /opt
RUN chown -R ubuntu:ubuntu /home/ubuntu

# 4. (可选) 如果之前日志里提示 .Xauthority 也有问题，可以顺便修一下，防止 VNC 报错
RUN touch /home/ubuntu/.Xauthority && \
    chown ubuntu:ubuntu /home/ubuntu/.Xauthority

# 5. 切回 ubuntu 用户，确保容器启动时的身份与原镜像保持一致
RUN pwd>/pp
USER ubuntu
