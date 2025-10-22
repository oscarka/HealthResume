#!/usr/bin/env python3
import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv("config.env")

async def test_deepseek():
    api_key = os.getenv("DEEPSEEK_API_KEY")
    base_url = "https://api.deepseek.com/v1/chat/completions"
    
    print(f"API Key: {api_key[:10]}..." if api_key else "API Key: None")
    print(f"Base URL: {base_url}")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一位专业的健康分析师和顾问，擅长分析健康数据并提供专业建议。"},
            {"role": "user", "content": "请生成一个简单的健康档案"}
        ],
        "temperature": 0.3,
        "max_tokens": 2000
    }
    
    print(f"发送请求到DeepSeek API...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(base_url, headers=headers, json=data)
            print(f"响应状态码: {response.status_code}")
            print(f"响应内容: {response.text[:500]}...")
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
    except httpx.TimeoutException as e:
        print(f"超时错误: {e}")
        return None
    except httpx.HTTPStatusError as e:
        print(f"HTTP错误: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        print(f"其他错误: {type(e).__name__}: {e}")
        return None

if __name__ == "__main__":
    result = asyncio.run(test_deepseek())
    print(f"结果: {result}")
