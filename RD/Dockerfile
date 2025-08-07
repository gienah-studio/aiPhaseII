FROM python:3.9-slim

WORKDIR /app

# 设置pip配置
COPY pip.conf /etc/pip.conf

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建上传目录
RUN mkdir -p uploads/enterprise/logo && \
    chmod -R 755 uploads

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9007"]
