# Railway 部署指南

## 部署步骤

### 1. 准备Railway账户
- 访问 [Railway.app](https://railway.app)
- 使用GitHub账户登录
- 连接你的GitHub仓库

### 2. 创建新项目
- 点击 "New Project"
- 选择 "Deploy from GitHub repo"
- 选择你的HealthResume仓库

### 3. 添加数据库服务
- 在项目仪表板中点击 "New"
- 选择 "Database" -> "MongoDB"
- 选择 "Database" -> "Neo4j"

### 4. 配置环境变量
在Railway项目设置中添加以下环境变量：

```
DEEPSEEK_API_KEY=你的DeepSeek API密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com
MONGODB_URL=从MongoDB服务获取的连接字符串
MONGODB_DATABASE=health_resume
NEO4J_URI=从Neo4j服务获取的连接字符串
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=从Neo4j服务获取的密码
DEBUG=False
HOST=0.0.0.0
PORT=8000
```

### 5. 部署配置
Railway会自动检测到以下配置文件：
- `railway.toml` - Railway部署配置
- `Procfile` - 进程启动命令
- `runtime.txt` - Python版本
- `requirements.txt` - Python依赖

### 6. 部署
- Railway会自动开始构建和部署
- 等待部署完成
- 获取部署URL

## 注意事项

1. **数据库连接**: Railway提供的MongoDB和Neo4j服务会自动配置连接字符串
2. **环境变量**: 确保在Railway控制台中正确设置所有环境变量
3. **API密钥**: 确保DeepSeek API密钥有效且有足够的配额
4. **端口**: Railway会自动设置PORT环境变量，应用会监听该端口

## 故障排除

### 常见问题
1. **构建失败**: 检查requirements.txt中的依赖版本
2. **数据库连接失败**: 检查MongoDB和Neo4j的环境变量
3. **API调用失败**: 检查DeepSeek API密钥是否正确

### 日志查看
- 在Railway项目仪表板中查看部署日志
- 检查应用启动日志和错误信息

## 更新部署
每次推送到GitHub主分支时，Railway会自动重新部署应用。
