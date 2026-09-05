#!/bin/bash

# MySQL数据库备份脚本

DB_USER="root"
DB_PASSWORD="123456"
DB_NAME="hnkj"
BACKUP_DIR="/root/YTMP/backups"
LOG_FILE="/root/YTMP/backups/backup.log"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${DATE}.sql"
COMPRESSED_FILE="${BACKUP_FILE}.gz"

mkdir -p "$BACKUP_DIR"

echo "[$(date)] 开始备份数据库: $DB_NAME" >> "$LOG_FILE"

mysqldump \
  -u"$DB_USER" \
  -p"$DB_PASSWORD" \
  --host=localhost \
  --port=3306 \
  --default-character-set=utf8mb4 \
  --single-transaction \
  --routines \
  --triggers \
  --events \
  --add-drop-database \
  --add-drop-table \
  --complete-insert \
  --disable-keys \
  --lock-tables=false \
  --databases "$DB_NAME" \
  > "$BACKUP_FILE" 2>> "$LOG_FILE"

if [ $? -eq 0 ] && [ -s "$BACKUP_FILE" ]; then
  gzip "$BACKUP_FILE"
  FILE_SIZE=$(du -h "$COMPRESSED_FILE" | cut -f1)
  echo "[$(date)] 备份完成: $(basename $COMPRESSED_FILE) (大小: $FILE_SIZE)" >> "$LOG_FILE"
  find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" -mtime +7 -delete
  echo "[$(date)] 已清理7天前的旧备份" >> "$LOG_FILE"
else
  echo "[$(date)] 备份失败！" >> "$LOG_FILE"
  rm -f "$BACKUP_FILE"
fi

echo "[$(date)] 备份任务结束" >> "$LOG_FILE"
echo "----------------------------------------" >> "$LOG_FILE"
