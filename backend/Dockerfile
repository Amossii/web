# 后端 Dockerfile - Flask 应用
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirements 文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p /app/train /app/logs

# 设置环境变量
ENV FLASK_APP=run.py
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 5000

# 健康检查（使用 curl，更轻量）
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# 启动命令
# 开发环境: python run.py
# 生产环境: 使用 gunicorn（推荐）
# 注意：run.py 中需要导出 app 实例供 gunicorn 使用
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "--preload", "run:app"]

