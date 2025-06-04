# 数据库初始化脚本

本目录包含数据库初始化相关的脚本和SQL文件。

## 文件说明

- `init_db.sql` - 数据库表结构SQL脚本
- `init_db.sh` - 数据库初始化Shell脚本

## 快速开始

### 使用Shell脚本初始化

```bash
# 进入backend目录
cd backend

# 执行初始化脚本
./scripts/init_db.sh
```

### 手动执行SQL脚本

#### PostgreSQL
```bash
# 创建数据库
createdb ai_template

# 执行SQL脚本
psql -d ai_template -f scripts/init_db.sql
```

#### MySQL
```bash
# 创建数据库
mysql -u root -p -e "CREATE DATABASE ai_template CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 执行SQL脚本
mysql -u root -p ai_template < scripts/init_db.sql
```

#### SQLite
```bash
# 创建数据目录
mkdir -p data

# 执行SQL脚本
sqlite3 data/ai_template.db < scripts/init_db.sql
```

## 数据库切换

项目支持一键切换数据库类型，只需修改环境变量：

### 切换到PostgreSQL
```bash
# .env文件中设置
DATABASE_TYPE=postgresql
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/ai_template
```

### 切换到MySQL
```bash
# .env文件中设置
DATABASE_TYPE=mysql
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=ai_template
```

### 切换到SQLite
```bash
# .env文件中设置
DATABASE_TYPE=sqlite
SQLITE_PATH=data/ai_template.db
```

## 依赖安装

### PostgreSQL
```bash
# macOS
brew install postgresql@14

# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# CentOS/RHEL
sudo yum install postgresql postgresql-server
```

### MySQL
```bash
# macOS
brew install mysql

# Ubuntu/Debian
sudo apt-get install mysql-server

# CentOS/RHEL
sudo yum install mysql-server
```

### SQLite
```bash
# macOS
brew install sqlite

# Ubuntu/Debian
sudo apt-get install sqlite3

# CentOS/RHEL
sudo yum install sqlite
```

## Python依赖

根据选择的数据库类型，需要安装相应的Python驱动：

```bash
# PostgreSQL
pip install asyncpg

# MySQL
pip install aiomysql

# SQLite
pip install aiosqlite
```

## 默认账户

初始化完成后，系统会创建一个默认管理员账户：

- **用户名**: admin
- **密码**: admin123
- **角色**: 管理员

⚠️ **安全提醒**: 请在生产环境中立即修改默认密码！

## 故障排除

### 连接失败
1. 检查数据库服务是否启动
2. 验证连接参数（主机、端口、用户名、密码）
3. 确认数据库已创建
4. 检查防火墙设置

### 权限问题
1. 确保数据库用户有足够权限
2. 检查文件系统权限（SQLite）
3. 验证SELinux设置（Linux）

### 编码问题
1. 确保数据库使用UTF-8编码
2. 检查客户端连接编码设置
3. 验证SQL文件编码格式

## 生产环境建议

1. **备份**: 定期备份数据库
2. **监控**: 设置数据库性能监控
3. **安全**: 使用强密码和SSL连接
4. **优化**: 根据负载调整连接池大小
5. **日志**: 启用慢查询日志 