#!/bin/bash

# AI Template 数据库初始化脚本
# 支持 PostgreSQL, MySQL, SQLite

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SQL_FILE="$SCRIPT_DIR/init_db.sql"

# 检查SQL文件是否存在
if [ ! -f "$SQL_FILE" ]; then
    log_error "SQL文件不存在: $SQL_FILE"
    exit 1
fi

# 读取环境变量
if [ -f "$PROJECT_ROOT/.env" ]; then
    log_info "加载环境变量文件: $PROJECT_ROOT/.env"
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

# 默认值
DATABASE_TYPE=${DATABASE_TYPE:-postgresql}
DATABASE_NAME=${DATABASE_NAME:-ai_template}

log_info "数据库类型: $DATABASE_TYPE"

case "$DATABASE_TYPE" in
    "postgresql")
        # PostgreSQL 配置
        POSTGRES_HOST=${POSTGRES_HOST:-localhost}
        POSTGRES_PORT=${POSTGRES_PORT:-5432}
        POSTGRES_USER=${POSTGRES_USER:-$(whoami)}
        POSTGRES_DB=${POSTGRES_DB:-$DATABASE_NAME}
        
        log_info "PostgreSQL配置:"
        log_info "  主机: $POSTGRES_HOST"
        log_info "  端口: $POSTGRES_PORT"
        log_info "  用户: $POSTGRES_USER"
        log_info "  数据库: $POSTGRES_DB"
        
        # 检查PostgreSQL是否可用
        if ! command -v psql &> /dev/null; then
            log_error "psql 命令未找到，请安装 PostgreSQL 客户端"
            exit 1
        fi
        
        # 检查数据库连接
        log_info "检查数据库连接..."
        if ! psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres -c '\q' 2>/dev/null; then
            log_error "无法连接到PostgreSQL服务器"
            log_info "请确保PostgreSQL服务正在运行，并且连接参数正确"
            exit 1
        fi
        
        # 创建数据库（如果不存在）
        log_info "创建数据库 $POSTGRES_DB（如果不存在）..."
        psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE $POSTGRES_DB;" 2>/dev/null || log_warning "数据库可能已存在"
        
        # 执行SQL脚本
        log_info "执行SQL初始化脚本..."
        psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$SQL_FILE"
        
        log_success "PostgreSQL数据库初始化完成！"
        ;;
        
    "mysql")
        # MySQL 配置
        MYSQL_HOST=${MYSQL_HOST:-localhost}
        MYSQL_PORT=${MYSQL_PORT:-3306}
        MYSQL_USER=${MYSQL_USER:-root}
        MYSQL_PASSWORD=${MYSQL_PASSWORD:-}
        MYSQL_DATABASE=${MYSQL_DATABASE:-$DATABASE_NAME}
        
        log_info "MySQL配置:"
        log_info "  主机: $MYSQL_HOST"
        log_info "  端口: $MYSQL_PORT"
        log_info "  用户: $MYSQL_USER"
        log_info "  数据库: $MYSQL_DATABASE"
        
        # 检查MySQL是否可用
        if ! command -v mysql &> /dev/null; then
            log_error "mysql 命令未找到，请安装 MySQL 客户端"
            exit 1
        fi
        
        # 构建MySQL连接参数
        MYSQL_OPTS="-h $MYSQL_HOST -P $MYSQL_PORT -u $MYSQL_USER"
        if [ -n "$MYSQL_PASSWORD" ]; then
            MYSQL_OPTS="$MYSQL_OPTS -p$MYSQL_PASSWORD"
        fi
        
        # 检查数据库连接
        log_info "检查数据库连接..."
        if ! mysql $MYSQL_OPTS -e 'SELECT 1;' 2>/dev/null; then
            log_error "无法连接到MySQL服务器"
            exit 1
        fi
        
        # 创建数据库（如果不存在）
        log_info "创建数据库 $MYSQL_DATABASE（如果不存在）..."
        mysql $MYSQL_OPTS -e "CREATE DATABASE IF NOT EXISTS $MYSQL_DATABASE CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        
        # 执行SQL脚本
        log_info "执行SQL初始化脚本..."
        mysql $MYSQL_OPTS "$MYSQL_DATABASE" < "$SQL_FILE"
        
        log_success "MySQL数据库初始化完成！"
        ;;
        
    "sqlite")
        # SQLite 配置
        SQLITE_PATH=${SQLITE_PATH:-$PROJECT_ROOT/data/ai_template.db}
        SQLITE_DIR=$(dirname "$SQLITE_PATH")
        
        log_info "SQLite配置:"
        log_info "  数据库文件: $SQLITE_PATH"
        
        # 检查SQLite是否可用
        if ! command -v sqlite3 &> /dev/null; then
            log_error "sqlite3 命令未找到，请安装 SQLite"
            exit 1
        fi
        
        # 创建目录（如果不存在）
        if [ ! -d "$SQLITE_DIR" ]; then
            log_info "创建目录: $SQLITE_DIR"
            mkdir -p "$SQLITE_DIR"
        fi
        
        # 执行SQL脚本
        log_info "执行SQL初始化脚本..."
        sqlite3 "$SQLITE_PATH" < "$SQL_FILE"
        
        log_success "SQLite数据库初始化完成！"
        log_info "数据库文件位置: $SQLITE_PATH"
        ;;
        
    *)
        log_error "不支持的数据库类型: $DATABASE_TYPE"
        log_info "支持的类型: postgresql, mysql, sqlite"
        exit 1
        ;;
esac

log_success "数据库初始化完成！"
log_info "默认管理员账户:"
log_info "  用户名: admin"
log_info "  密码: admin123"
log_warning "请在生产环境中修改默认密码！" 