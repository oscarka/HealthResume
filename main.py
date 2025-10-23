from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pymongo import MongoClient
import os
import uuid
import json
from datetime import datetime
from dotenv import load_dotenv
import httpx
from bson import ObjectId
from neo4j import GraphDatabase

# 加载环境变量
load_dotenv("config.env")

app = FastAPI(title="个人健康知识图谱系统 - 第一阶段")

# MongoDB连接
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "health_resume")

# Neo4j连接
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

try:
    client = MongoClient(MONGODB_URL)
    db = client[MONGODB_DATABASE]
    # 测试连接
    client.admin.command('ping')
    print("MongoDB连接成功")
except Exception as e:
    print(f"MongoDB连接失败: {e}")
    db = None

# Neo4j连接
try:
    neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    # 测试连接
    with neo4j_driver.session() as session:
        session.run("RETURN 1")
    print("Neo4j连接成功")
except Exception as e:
    print(f"Neo4j连接失败: {e}")
    neo4j_driver = None

# DeepSeek API配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# 数据模型
class ConversationUpload(BaseModel):
    content: str

class HealthQuestion(BaseModel):
    question: str

class ExtractionResult(BaseModel):
    session_id: str
    entities: list
    relations: list
    created_at: str

# DeepSeek知识提取服务
class DeepSeekExtractor:
    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
        self.base_url = DEEPSEEK_BASE_URL
        
    async def extract_knowledge(self, conversation: str) -> dict:
        """使用DeepSeek API提取知识"""
        print(f"开始知识提取，API Key: {self.api_key[:10]}..." if self.api_key else "API Key: None")
        
        if not self.api_key or self.api_key == "your_deepseek_api_key_here":
            print("使用模拟数据进行测试")
            # 返回模拟数据用于测试
            return {
                "entities": [
                    {"name": "头痛", "type": "症状", "confidence": 0.95},
                    {"name": "发热", "type": "症状", "confidence": 0.88},
                    {"name": "感冒", "type": "疾病", "confidence": 0.82}
                ],
                "relations": [
                    {"type": "HAS_SYMPTOM", "source": "患者", "target": "头痛", "confidence": 0.90},
                    {"type": "HAS_SYMPTOM", "source": "患者", "target": "发热", "confidence": 0.85},
                    {"type": "SYMPTOM_OF", "source": "头痛", "target": "感冒", "confidence": 0.80}
                ]
            }
        
        print("使用真实API进行知识提取")
            
        prompt = f"""
你是一个专业的医疗信息提取专家。请从以下医患对话中提取医疗实体和关系。

对话内容：
{conversation}

请按照以下JSON格式返回提取结果：
{{
    "entities": [
        {{
            "name": "实体名称",
            "type": "实体类型（症状/疾病/药物/检查/治疗）",
            "confidence": 0.95
        }}
    ],
    "relations": [
        {{
            "type": "关系类型（HAS_SYMPTOM/SYMPTOM_OF/TREATS等）",
            "source": "源实体",
            "target": "目标实体", 
            "confidence": 0.88
        }}
    ]
}}

要求：
1. 准确识别医疗实体（症状、疾病、药物、检查、治疗等）
2. 识别实体间的关系
3. 置信度范围0-1
4. 只返回JSON格式，不要其他文字
"""

        try:
            print(f"发送请求到DeepSeek API进行知识提取...")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.1,
                        "max_tokens": 2000
                    },
                    timeout=30.0
                )
                
                print(f"知识提取API响应状态码: {response.status_code}")
                print(f"知识提取API响应内容: {response.text[:500]}...")
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    print(f"知识提取成功，内容: {content[:200]}...")
                    
                    # 尝试解析JSON
                    try:
                        extracted_data = json.loads(content)
                        return extracted_data
                    except json.JSONDecodeError:
                        # 如果JSON解析失败，返回默认结构
                        return {
                            "entities": [],
                            "relations": []
                        }
                else:
                    raise HTTPException(status_code=500, detail=f"DeepSeek API错误: {response.text}")
                    
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"知识提取失败: {str(e)}")

extractor = DeepSeekExtractor()

# 健康分析服务
class HealthAnalysisService:
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
        
    def get_user_health_summary(self, user_id: str = "default_user"):
        """获取用户健康信息摘要"""
        if not self.driver:
            raise HTTPException(status_code=500, detail="Neo4j连接失败")
            
        with self.driver.session() as session:
            # 获取用户的所有健康信息
            result = session.run("""
                MATCH (u:User {user_id: $user_id})
                OPTIONAL MATCH (u)-[r1:HAS_SYMPTOM]->(s:Entity)
                OPTIONAL MATCH (u)-[r2:HAS_DIAGNOSIS]->(d:Entity)
                OPTIONAL MATCH (u)-[r3:USES_MEDICATION]->(m:Entity)
                OPTIONAL MATCH (u)-[r4:HAS_TREATMENT]->(t:Entity)
                OPTIONAL MATCH (u)-[r5:HAS_TEST]->(test:Entity)
                RETURN 
                    collect(DISTINCT {name: s.name, type: s.type, confidence: r1.confidence, created_at: r1.created_at}) as symptoms,
                    collect(DISTINCT {name: d.name, type: d.type, confidence: r2.confidence, created_at: r2.created_at}) as diseases,
                    collect(DISTINCT {name: m.name, type: m.type, confidence: r3.confidence, created_at: r3.created_at}) as medications,
                    collect(DISTINCT {name: t.name, type: t.type, confidence: r4.confidence, created_at: r4.created_at}) as treatments,
                    collect(DISTINCT {name: test.name, type: test.type, confidence: r5.confidence, created_at: r5.created_at}) as tests
            """, user_id=user_id)
            
            record = result.single()
            if not record:
                return {
                    "symptoms": [],
                    "diseases": [],
                    "medications": [],
                    "treatments": [],
                    "tests": []
                }
                
            return {
                "symptoms": [item for item in record["symptoms"] if item["name"]],
                "diseases": [item for item in record["diseases"] if item["name"]],
                "medications": [item for item in record["medications"] if item["name"]],
                "treatments": [item for item in record["treatments"] if item["name"]],
                "tests": [item for item in record["tests"] if item["name"]]
            }
    
    def format_health_data_for_llm(self, health_data: dict) -> str:
        """将健康数据格式化为LLM可理解的文本"""
        text = "用户健康信息：\n\n"
        
        if health_data["symptoms"]:
            text += "症状：\n"
            for symptom in health_data["symptoms"]:
                text += f"- {symptom['name']} (置信度: {symptom['confidence']:.2f})\n"
            text += "\n"
            
        if health_data["diseases"]:
            text += "疾病：\n"
            for disease in health_data["diseases"]:
                text += f"- {disease['name']} (置信度: {disease['confidence']:.2f})\n"
            text += "\n"
            
        if health_data["medications"]:
            text += "药物：\n"
            for med in health_data["medications"]:
                text += f"- {med['name']} (置信度: {med['confidence']:.2f})\n"
            text += "\n"
            
        if health_data["treatments"]:
            text += "治疗：\n"
            for treatment in health_data["treatments"]:
                text += f"- {treatment['name']} (置信度: {treatment['confidence']:.2f})\n"
            text += "\n"
            
        if health_data["tests"]:
            text += "检查：\n"
            for test in health_data["tests"]:
                text += f"- {test['name']} (置信度: {test['confidence']:.2f})\n"
            text += "\n"
                
        return text

# 健康分析LLM服务
class HealthAnalysisLLM:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        
    async def generate_health_profile(self, health_data_text: str) -> dict:
        """生成健康档案"""
        prompt = f"""
你是一位专业的健康分析师。请基于以下用户的健康图谱数据，生成一份简洁明了的个人健康档案。

用户健康数据：
{health_data_text}

请生成包含以下内容的健康档案（使用JSON格式）：
1. "当前状况" - 用户当前的主要健康状态
2. "主要问题" - 识别出的主要健康问题
3. "用药情况" - 当前用药情况分析
4. "健康建议" - 基于数据的个性化健康建议
5. "风险评估" - 潜在的健康风险

要求：
- 回答要专业、准确、易懂
- 基于提供的数据进行分析
- 如果数据不足，请明确说明
- 使用JSON格式输出
"""
        
        try:
            print(f"正在调用DeepSeek API生成健康档案...")
            response = await self._call_deepseek_api(prompt)
            print(f"DeepSeek API响应: {response[:200]}...")
            return {
                "success": True,
                "profile": response,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"生成健康档案失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def answer_health_question(self, question: str, health_data_text: str) -> dict:
        """回答健康问题"""
        prompt = f"""
你是一位专业的健康顾问。请基于用户的健康图谱数据回答用户的问题。

用户问题：{question}

用户健康数据：
{health_data_text}

请提供准确、专业的回答，要求：
1. 基于图谱数据进行分析
2. 如果图谱中没有相关信息，请明确说明
3. 回答要专业但易懂
4. 提供相关的健康建议（如果适用）
5. 评估回答的置信度（基于数据的完整性）

请使用JSON格式输出：
{{
    "answer": "回答内容",
    "confidence": "置信度评估",
    "data_source": "数据来源说明",
    "suggestions": "相关建议"
}}
"""
        
        try:
            response = await self._call_deepseek_api(prompt)
            return {
                "success": True,
                "question": question,
                "answer": response,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _call_deepseek_api(self, prompt: str) -> str:
        """调用DeepSeek API"""
        print(f"API Key: {self.api_key[:10]}..." if self.api_key else "API Key: None")
        print(f"Base URL: {self.base_url}")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是一位专业的健康分析师和顾问，擅长分析健康数据并提供专业建议。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 2000
        }
        
        print(f"发送请求到DeepSeek API...")
        print(f"请求头: {headers}")
        print(f"请求数据: {data}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(self.base_url, headers=headers, json=data)
                print(f"响应状态码: {response.status_code}")
                print(f"响应头: {dict(response.headers)}")
                print(f"响应内容: {response.text[:500]}...")
                
                if response.status_code != 200:
                    print(f"HTTP错误: {response.status_code} - {response.text}")
                    raise Exception(f"HTTP {response.status_code}: {response.text}")
                
                response.raise_for_status()
                result = response.json()
                print(f"解析后的结果: {result}")
                
                if "choices" not in result or len(result["choices"]) == 0:
                    print(f"API响应格式错误: {result}")
                    raise Exception(f"API响应格式错误: {result}")
                
                content = result["choices"][0]["message"]["content"]
                print(f"提取的内容: {content[:200]}...")
                return content
                
            except httpx.TimeoutException as e:
                print(f"请求超时: {e}")
                raise Exception(f"请求超时: {e}")
            except httpx.HTTPStatusError as e:
                print(f"HTTP状态错误: {e.response.status_code} - {e.response.text}")
                raise Exception(f"HTTP {e.response.status_code}: {e.response.text}")
            except Exception as e:
                print(f"其他错误: {type(e).__name__}: {e}")
                raise

# 初始化服务
health_analysis_service = HealthAnalysisService(neo4j_driver)
health_analysis_llm = HealthAnalysisLLM()

# 图谱构建服务
class KnowledgeGraphBuilder:
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
        
    def build_user_knowledge_graph(self, session_id: str, user_id: str = "default_user"):
        """构建用户知识图谱"""
        if not self.driver:
            raise HTTPException(status_code=500, detail="Neo4j连接失败")
            
        # 从MongoDB获取提取结果
        extraction = db.extractions.find_one({"session_id": session_id})
        if not extraction:
            raise HTTPException(status_code=404, detail="提取结果不存在")
            
        with self.driver.session() as session:
            # 创建或更新用户节点
            session.run("""
                MERGE (u:User {user_id: $user_id})
                SET u.last_updated = datetime()
            """, user_id=user_id)
            
            # 处理实体
            for entity in extraction.get("entities", []):
                entity_name = entity.get("name", "")
                entity_type = entity.get("type", "")
                confidence = entity.get("confidence", 0.0)
                
                if entity_name and entity_type:
                    # 创建实体节点
                    session.run("""
                        MERGE (e:Entity {name: $name, type: $type})
                        SET e.confidence = $confidence,
                            e.last_updated = datetime(),
                            e.source_session = $session_id
                    """, name=entity_name, type=entity_type, confidence=confidence, session_id=session_id)
                    
                    # 创建用户与实体的关系
                    if entity_type == "症状":
                        session.run("""
                            MATCH (u:User {user_id: $user_id})
                            MATCH (e:Entity {name: $name, type: $type})
                            MERGE (u)-[r:HAS_SYMPTOM]->(e)
                            SET r.confidence = $confidence,
                                r.session_id = $session_id,
                                r.created_at = datetime()
                        """, user_id=user_id, name=entity_name, type=entity_type, confidence=confidence, session_id=session_id)
                    elif entity_type == "疾病":
                        session.run("""
                            MATCH (u:User {user_id: $user_id})
                            MATCH (e:Entity {name: $name, type: $type})
                            MERGE (u)-[r:HAS_DIAGNOSIS]->(e)
                            SET r.confidence = $confidence,
                                r.session_id = $session_id,
                                r.created_at = datetime()
                        """, user_id=user_id, name=entity_name, type=entity_type, confidence=confidence, session_id=session_id)
                    elif entity_type == "药物":
                        session.run("""
                            MATCH (u:User {user_id: $user_id})
                            MATCH (e:Entity {name: $name, type: $type})
                            MERGE (u)-[r:USES_MEDICATION]->(e)
                            SET r.confidence = $confidence,
                                r.session_id = $session_id,
                                r.created_at = datetime()
                        """, user_id=user_id, name=entity_name, type=entity_type, confidence=confidence, session_id=session_id)
            
            # 处理关系
            for relation in extraction.get("relations", []):
                relation_type = relation.get("type", "")
                source = relation.get("source", "")
                target = relation.get("target", "")
                confidence = relation.get("confidence", 0.0)
                
                if relation_type and source and target:
                    session.run("""
                        MATCH (s:Entity {name: $source})
                        MATCH (t:Entity {name: $target})
                        MERGE (s)-[r:RELATION {type: $relation_type}]->(t)
                        SET r.confidence = $confidence,
                            r.session_id = $session_id,
                            r.created_at = datetime()
                    """, source=source, target=target, relation_type=relation_type, confidence=confidence, session_id=session_id)
    
    def get_user_knowledge_graph(self, user_id: str = "default_user"):
        """获取用户知识图谱数据"""
        if not self.driver:
            raise HTTPException(status_code=500, detail="Neo4j连接失败")
            
        try:
            with self.driver.session() as session:
                # 查询所有节点
                nodes_result = session.run("""
                    MATCH (n)
                    WHERE n:User OR n:Entity
                    RETURN n
                """)
                
                # 查询所有关系
                edges_result = session.run("""
                    MATCH (a)-[r]->(b)
                    RETURN a, r, b
                """)
                
                nodes = []
                edges = []
                node_ids = set()
                
                # 处理节点
                for record in nodes_result:
                    node_data = dict(record["n"])
                    
                    if "user_id" in node_data:
                        # 用户节点
                        node_id = node_data["user_id"]
                        if node_id not in node_ids:
                            nodes.append({
                                "id": node_id,
                                "label": "用户",
                                "type": "User",
                                "group": "user"
                            })
                            node_ids.add(node_id)
                    elif "name" in node_data and "type" in node_data:
                        # 实体节点
                        node_id = f"{node_data['name']}_{node_data['type']}"
                        if node_id not in node_ids:
                            nodes.append({
                                "id": node_id,
                                "label": node_data["name"],
                                "type": node_data["type"],
                                "group": node_data["type"].lower(),
                                "confidence": node_data.get("confidence", 0.0)
                            })
                            node_ids.add(node_id)
                
                # 处理关系
                for record in edges_result:
                    source_data = dict(record["a"])
                    target_data = dict(record["b"])
                    rel = record["r"]
                    
                    # 确定源节点ID
                    if "user_id" in source_data:
                        source_id = source_data["user_id"]
                    elif "name" in source_data and "type" in source_data:
                        source_id = f"{source_data['name']}_{source_data['type']}"
                    else:
                        continue
                    
                    # 确定目标节点ID
                    if "user_id" in target_data:
                        target_id = target_data["user_id"]
                    elif "name" in target_data and "type" in target_data:
                        target_id = f"{target_data['name']}_{target_data['type']}"
                    else:
                        continue
                    
                    # 获取关系类型
                    rel_type = rel.type if hasattr(rel, 'type') else 'RELATION'
                    
                    edges.append({
                        "id": f"{source_id}_{target_id}_{rel_type}",
                        "source": source_id,
                        "target": target_id,
                        "label": rel_type,
                        "confidence": 0.0
                    })
                
                return {
                    "nodes": nodes,
                    "edges": edges
                }
        except Exception as e:
            print(f"图谱查询错误: {e}")
            raise HTTPException(status_code=500, detail=f"获取图谱失败: {str(e)}")

graph_builder = KnowledgeGraphBuilder(neo4j_driver)

# API路由
@app.post("/upload")
async def upload_conversation(conversation: ConversationUpload):
    """上传对话"""
    if db is None:
        raise HTTPException(status_code=500, detail="数据库连接失败")
    
    # 生成会话ID
    session_id = f"SESS_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    
    # 存储对话
    conversation_doc = {
        "session_id": session_id,
        "content": conversation.content,
        "created_at": datetime.now().isoformat(),
        "processed": False
    }
    
    try:
        result = db.conversations.insert_one(conversation_doc)
        return {
            "success": True,
            "session_id": session_id,
            "message": "对话上传成功"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"存储失败: {str(e)}")

@app.post("/extract/{session_id}")
async def extract_knowledge(session_id: str):
    """提取知识"""
    if db is None:
        raise HTTPException(status_code=500, detail="数据库连接失败")
    
    # 查找对话
    conversation = db.conversations.find_one({"session_id": session_id})
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")
    
    try:
        # 提取知识
        extraction_result = await extractor.extract_knowledge(conversation["content"])
        
        # 存储提取结果
        extraction_doc = {
            "session_id": session_id,
            "entities": extraction_result.get("entities", []),
            "relations": extraction_result.get("relations", []),
            "created_at": datetime.now().isoformat()
        }
        
        result = db.extractions.insert_one(extraction_doc)
        
        # 更新对话状态
        db.conversations.update_one(
            {"session_id": session_id},
            {"$set": {"processed": True}}
        )
        
        # 构建知识图谱
        try:
            graph_builder.build_user_knowledge_graph(session_id)
        except Exception as e:
            print(f"图谱构建失败: {e}")
        
        # 移除ObjectId以避免序列化错误
        extraction_doc.pop("_id", None)
        
        return {
            "success": True,
            "session_id": session_id,
            "extraction": extraction_doc
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"知识提取失败: {str(e)}")

@app.get("/result/{session_id}")
async def get_result(session_id: str):
    """获取提取结果"""
    if db is None:
        raise HTTPException(status_code=500, detail="数据库连接失败")
    
    # 查找提取结果
    result = db.extractions.find_one({"session_id": session_id})
    if not result:
        raise HTTPException(status_code=404, detail="提取结果不存在")
    
    # 移除ObjectId以避免序列化错误
    result.pop("_id", None)
    
    return {
        "success": True,
        "session_id": session_id,
        "entities": result["entities"],
        "relations": result["relations"],
        "created_at": result["created_at"]
    }

@app.get("/graph/{user_id}")
async def get_knowledge_graph(user_id: str = "default_user"):
    """获取用户知识图谱"""
    try:
        graph_data = graph_builder.get_user_knowledge_graph(user_id)
        return {
            "success": True,
            "user_id": user_id,
            "graph": graph_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取图谱失败: {str(e)}")

@app.post("/graph/build/{session_id}")
async def build_knowledge_graph(session_id: str, user_id: str = "default_user"):
    """手动构建知识图谱"""
    try:
        graph_builder.build_user_knowledge_graph(session_id, user_id)
        return {
            "success": True,
            "session_id": session_id,
            "user_id": user_id,
            "message": "图谱构建成功"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图谱构建失败: {str(e)}")

# 第三阶段：智能健康问答API

@app.get("/health/profile/{user_id}")
async def generate_health_profile(user_id: str = "default_user"):
    """生成个人健康档案"""
    try:
        # 获取用户健康数据
        health_data = health_analysis_service.get_user_health_summary(user_id)
        
        # 检查是否有数据
        total_items = (len(health_data["symptoms"]) + len(health_data["diseases"]) + 
                      len(health_data["medications"]) + len(health_data["treatments"]) + 
                      len(health_data["tests"]))
        
        if total_items == 0:
            return {
                "success": False,
                "message": "用户暂无健康数据，请先上传对话记录",
                "user_id": user_id
            }
        
        # 格式化数据
        health_data_text = health_analysis_service.format_health_data_for_llm(health_data)
        print(f"格式化后的健康数据: {health_data_text[:200]}...")
        
        # 生成健康档案
        result = await health_analysis_llm.generate_health_profile(health_data_text)
        print(f"LLM调用结果: {result}")
        
        return {
            "success": result["success"],
            "user_id": user_id,
            "health_data": health_data,
            "profile": result.get("profile"),
            "error": result.get("error"),
            "timestamp": result["timestamp"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成健康档案失败: {str(e)}")

@app.post("/health/ask/{user_id}")
async def ask_health_question(user_id: str, question_data: HealthQuestion):
    """智能健康问答"""
    try:
        question = question_data.question
        # 获取用户健康数据
        health_data = health_analysis_service.get_user_health_summary(user_id)
        
        # 检查是否有数据
        total_items = (len(health_data["symptoms"]) + len(health_data["diseases"]) + 
                      len(health_data["medications"]) + len(health_data["treatments"]) + 
                      len(health_data["tests"]))
        
        if total_items == 0:
            return {
                "success": False,
                "message": "用户暂无健康数据，请先上传对话记录",
                "user_id": user_id,
                "question": question
            }
        
        # 格式化数据
        health_data_text = health_analysis_service.format_health_data_for_llm(health_data)
        
        # 回答健康问题
        result = await health_analysis_llm.answer_health_question(question, health_data_text)
        
        return {
            "success": result["success"],
            "user_id": user_id,
            "question": question,
            "answer": result.get("answer"),
            "error": result.get("error"),
            "timestamp": result["timestamp"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"健康问答失败: {str(e)}")

@app.get("/health/summary/{user_id}")
async def get_health_summary(user_id: str = "default_user"):
    """获取用户健康数据摘要（不调用LLM）"""
    try:
        health_data = health_analysis_service.get_user_health_summary(user_id)
        
        # 计算统计信息
        stats = {
            "total_symptoms": len(health_data["symptoms"]),
            "total_diseases": len(health_data["diseases"]),
            "total_medications": len(health_data["medications"]),
            "total_treatments": len(health_data["treatments"]),
            "total_tests": len(health_data["tests"]),
            "total_items": (len(health_data["symptoms"]) + len(health_data["diseases"]) + 
                           len(health_data["medications"]) + len(health_data["treatments"]) + 
                           len(health_data["tests"]))
        }
        
        return {
            "success": True,
            "user_id": user_id,
            "health_data": health_data,
            "statistics": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取健康摘要失败: {str(e)}")

# 静态文件服务
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """首页 - 官网首页"""
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """仪表板页面"""
    with open("static/dashboard.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/result", response_class=HTMLResponse)
async def result_page():
    """结果页面"""
    with open("static/result.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
