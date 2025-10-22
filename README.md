# 个人健康知识图谱系统 - 第一阶段

## 系统简介

这是个人健康知识图谱系统的第一阶段实现，主要功能包括：
- 对话上传：用户可以上传医患对话文本
- 知识提取：使用DeepSeek API自动提取医疗实体和关系
- 结果查看：以表格形式展示提取的实体和关系

## 安装和配置

### 1. MongoDB安装

由于网络问题，推荐使用Docker安装MongoDB：

```bash
# 使用Docker安装MongoDB
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

或者手动安装：
1. 访问 https://www.mongodb.com/try/download/community
2. 下载macOS版本
3. 安装并启动服务

### 2. 配置API Key

编辑 `config.env` 文件，设置您的DeepSeek API Key：

```bash
# 将your_deepseek_api_key_here替换为您的实际API Key
DEEPSEEK_API_KEY=sk-your-actual-api-key-here
```

### 3. 安装Python依赖

```bash
pip3 install -r requirements.txt
```

## 启动系统

### 方法1：使用启动脚本（推荐）

```bash
./start.sh
```

### 方法2：手动启动

```bash
# 确保MongoDB运行
brew services start mongodb/brew/mongodb-community

# 启动应用
python3 main.py
```

## 使用说明

1. **访问系统**：打开浏览器访问 http://localhost:8000

2. **上传对话**：
   - 在文本框中输入医患对话
   - 点击"上传对话"按钮
   - 系统会生成会话ID并自动跳转到结果页面

3. **查看结果**：
   - 系统会自动提取医疗实体和关系
   - 实体表格显示：实体名称、类型、置信度
   - 关系表格显示：关系类型、源实体、目标实体、置信度

## 技术架构

- **后端**：FastAPI + MongoDB
- **前端**：HTML + JavaScript（原生）
- **LLM**：DeepSeek API
- **部署**：本地单机部署

## API接口

- `POST /upload` - 上传对话
- `POST /extract/{session_id}` - 提取知识
- `GET /result/{session_id}` - 获取结果

## 故障排除

### MongoDB连接失败
```bash
# 检查MongoDB是否运行
brew services list | grep mongodb

# 启动MongoDB
brew services start mongodb/brew/mongodb-community
```

### API Key错误
- 检查config.env文件中的DEEPSEEK_API_KEY是否正确
- 确保API Key有效且有足够额度

### 端口占用
- 默认端口8000被占用时，修改main.py中的端口号

## 下一步

第一阶段完成后，将进入第二阶段：
- 集成Neo4j图数据库
- 构建个人健康知识图谱
- 提供图谱可视化功能
