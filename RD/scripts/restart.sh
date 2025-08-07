#!/bin/bash

# 设置颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 输出带颜色的消息
print_success() {
    echo -e "${GREEN}$1${NC}"
}

print_error() {
    echo -e "${RED}$1${NC}"
}

# 检查命令是否执行成功
check_status() {
    if [ $? -eq 0 ]; then
        print_success "$1"
    else
        print_error "$2"
        exit 1
    fi
}

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    print_error "Docker 未运行，请先启动 Docker"
    exit 1
fi

echo "开始重启应用..."

# 停止现有容器
echo "停止现有容器..."
docker-compose down
check_status "容器已停止" "停止容器失败"

# 删除旧的构建缓存
echo "清理构建缓存..."
docker-compose rm -f
check_status "缓存已清理" "清理缓存失败"

# 重新构建镜像
echo "重新构建镜像..."
docker-compose build
check_status "镜像构建成功" "构建镜像失败"

# 启动新容器
echo "启动新容器..."
docker-compose up -d
check_status "容器启动成功" "启动容器失败"

# 检查容器状态
echo "检查容器状态..."
docker-compose ps
check_status "容器状态检查完成" "状态检查失败"

# 显示容器日志
echo "显示应用日志..."
docker-compose logs -f app 