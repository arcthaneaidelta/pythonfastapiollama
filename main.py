from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import requests
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Chat Completions API", version="1.0.0")

# Configuration
OLLAMA_EMAIL = os.getenv("OLLAMA_EMAIL", "vladdracule.techman47@gmail.com") 
OLLAMA_PASSWORD = os.getenv("OLLAMA_PASSWORD", "Admin123@")   
OLLAMA_BASE_URL = "http://89.116.38.103:8080"
API_KEY = os.getenv("API_KEY", "sk-gGS9zMUIYpctaVh82k70ReeUePzgoQ87")

# Session management
session_cookies = None
session_expires_at = None

# Security
security = HTTPBearer()

class Message(BaseModel):
    role: str = "user"  # Default role set to "user"
    content: str

class ChatRequest(BaseModel):
    model: str = "llama3.2:1b"  # Default model set to llama3.2:1b
    messages: list[Message]
    temperature: float = 0.7

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify the API key from Bearer token"""
    if credentials.credentials != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

def get_web_session():
    global session_cookies, session_expires_at
    
    if session_cookies and session_expires_at and datetime.now() < session_expires_at:
        return session_cookies
    
    session = requests.Session()
    
    try:
        logger.info("Authenticating with Open WebUI...")
        
        login_page_response = session.get(f"{OLLAMA_BASE_URL}/auth", timeout=30)
        logger.info(f"Login page response: {login_page_response.status_code}")
        
        auth_endpoints = [
            "/api/v1/auths/signin",
            "/api/auths/signin", 
            "/auth/signin",
            "/signin",
            "/api/auth/signin",
            "/api/v1/auth/signin"
        ]
        
        for endpoint in auth_endpoints:
            try:
                logger.info(f"Trying authentication endpoint: {endpoint}")
                
                auth_response = session.post(
                    f"{OLLAMA_BASE_URL}{endpoint}",
                    json={
                        "email": OLLAMA_EMAIL,
                        "password": OLLAMA_PASSWORD
                    },
                    timeout=30
                )
                
                logger.info(f"Auth endpoint {endpoint} response: {auth_response.status_code}")
                logger.info(f"Response text: {auth_response.text[:200]}")
                
                if auth_response.status_code == 200:
                    try:
                        auth_data = auth_response.json()
                        logger.info(f"Successful auth response: {auth_data}")
                        session_cookies = session.cookies
                        session_expires_at = datetime.now() + timedelta(hours=2)
                        
                        return session_cookies
                        
                    except Exception as e:
                        logger.info(f"Response not JSON, checking for success indicators: {e}")

                        if "success" in auth_response.text.lower() or auth_response.status_code == 200:
                            session_cookies = session.cookies
                            session_expires_at = datetime.now() + timedelta(hours=2)
                            return session_cookies
                            
            except Exception as e:
                logger.error(f"Error with endpoint {endpoint}: {e}")
                continue
        
        logger.error("All authentication endpoints failed")
        return None
        
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return None

def make_authenticated_request(method, endpoint, **kwargs):
    """Make an authenticated request using session cookies"""
    cookies = get_web_session()
    if not cookies:
        raise HTTPException(status_code=401, detail="Authentication failed")
    
    kwargs['cookies'] = cookies

    headers = kwargs.get('headers', {})
    headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Content-Type': 'application/json',
        'Origin': OLLAMA_BASE_URL,
        'Referer': f"{OLLAMA_BASE_URL}/"
    })
    kwargs['headers'] = headers
    
    url = f"{OLLAMA_BASE_URL}{endpoint}"
    
    if method.upper() == 'GET':
        return requests.get(url, **kwargs)
    elif method.upper() == 'POST':
        return requests.post(url, **kwargs)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest, api_key: str = Depends(verify_api_key)):
    logger.info(f"Received chat request for model: {request.model}")
    logger.info(f"Messages: {[{'role': msg.role, 'content': msg.content[:100]} for msg in request.messages]}")
    
    # Validate configuration
    if OLLAMA_EMAIL == "your_email@example.com":
        raise HTTPException(
            status_code=500, 
            detail="Please configure OLLAMA_EMAIL and OLLAMA_PASSWORD"
        )
    

    processed_messages = []
    for msg in request.messages:
        processed_msg = {
            "role": msg.role if msg.role in ["user", "assistant", "system"] else "user",
            "content": msg.content
        }
        processed_messages.append(processed_msg)
    
    try:
        cookies = get_web_session()
        if not cookies:
            raise HTTPException(status_code=401, detail="Failed to authenticate with Open WebUI")
        logger.info("Authentication successful")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication error: {str(e)}")

    chat_endpoints = [
        {
            "endpoint": "/api/v1/chat/completions",
            "payload": {
                "model": request.model,
                "messages": processed_messages,
                "temperature": request.temperature,
                "stream": False
            }
        },
        {
            "endpoint": "/api/chat/completions", 
            "payload": {
                "model": request.model,
                "messages": processed_messages,
                "temperature": request.temperature,
                "stream": False
            }
        },
        {
            "endpoint": "/ollama/v1/chat/completions",
            "payload": {
                "model": request.model,
                "messages": processed_messages,
                "temperature": request.temperature,
                "stream": False
            }
        },
        {
            "endpoint": "/api/generate",
            "payload": {
                "model": request.model,
                "prompt": "\n".join([f"{msg['role']}: {msg['content']}" for msg in processed_messages]) + "\nassistant:",
                "stream": False,
                "temperature": request.temperature
            }
        },
        {
            "endpoint": "/ollama/api/generate",
            "payload": {
                "model": request.model,
                "prompt": "\n".join([f"{msg['role']}: {msg['content']}" for msg in processed_messages]) + "\nassistant:",
                "stream": False,
                "temperature": request.temperature
            }
        }
    ]
    
    errors = []
    
    for chat_config in chat_endpoints:
        try:
            logger.info(f"Trying endpoint: {chat_config['endpoint']}")
            
            response = make_authenticated_request(
                "POST",
                chat_config["endpoint"],
                json=chat_config["payload"],
                timeout=60
            )
            
            logger.info(f"Endpoint {chat_config['endpoint']} response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                if "choices" in data:
                    return data
                elif "response" in data:
                    response_text = data.get("response", "").strip()
                    return {
                        "id": "chatcmpl-webui",
                        "object": "chat.completion", 
                        "created": int(datetime.now().timestamp()),
                        "model": request.model,
                        "choices": [{
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": response_text
                            },
                            "finish_reason": "stop"
                        }],
                        "usage": {
                            "prompt_tokens": len(str(processed_messages).split()),
                            "completion_tokens": len(response_text.split()),
                            "total_tokens": len(str(processed_messages).split()) + len(response_text.split())
                        }
                    }
                else:
                    return data
                    
            else:
                errors.append(f"{chat_config['endpoint']}: {response.status_code} - {response.text[:200]}")
                
        except Exception as e:
            errors.append(f"{chat_config['endpoint']}: {str(e)}")
            logger.error(f"Endpoint {chat_config['endpoint']} exception: {e}")
    
    raise HTTPException(
        status_code=500,
        detail=f"All Open WebUI chat endpoints failed. Errors: {'; '.join(errors)}"
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Chat Completions API",
        "version": "1.0.0",
        "endpoints": {
            "chat": "/v1/chat/completions",
            "health": "/health"
        },
        "authentication": "Bearer token required"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))  
    print(f"Starting server with API Key: {API_KEY}")
    print("Set environment variable API_KEY to change the authentication key")
    uvicorn.run(app, host="0.0.0.0", port=port)