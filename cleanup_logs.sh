#!/bin/bash

# 日志清理脚本
# 清理7天前的日志文件

echo "[$(date)] 开始清理日志..."

# 清理Nginx旧日志（保留7天）
find /var/log/nginx/ -name "*.log.*" -mtime +7 -delete
echo "已清理Nginx旧日志"

# 清理应用日志（保留7天）
if [ -d "/root/YTMP/logs" ]; then
  find /root/YTMP/logs/ -name "*.log" -mtime +7 -delete
  echo "已清理应用日志"
fi

# 清理Docker容器日志（限制最大100MB）
for container in $(docker ps -q); do
  log_path=$(docker inspect "$container" --format='{{.LogPath}}' 2>/dev/null)
  if [ -f "$log_path" ]; then
    log_size=$(du -m "$log_path" | cut -f1)
    if [ "$log_size" -gt 100 ]; then
      truncate -s 0 "$log_path"
      echo "已清理容器 $(docker inspect "$container" --format='{{.Name}}') 日志 (${log_size}MB)"
    fi
  fi
done

# 清理Flask应用日志
find /root/YTMP -name "app.log" -size +50M -exec truncate -s 0 {} \;
echo "已清理Flask应用日志"

echo "[$(date)] 日志清理完成"
echo "----------------------------------------"
