# main.py
from typing import List
from fastapi import FastAPI, HTTPException,Security,Depends, HTTPException, status
from fastapi import Request

from fastapi.middleware.cors import CORSMiddleware
from tortoise.contrib.fastapi import register_tortoise
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from tortoise.contrib.pydantic import pydantic_model_creator

from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from datetime import datetime, timedelta
from jose import JWTError, jwt

import random
import string
from models import LotteryTicket,AdminUser

from pydantic import BaseModel

class TokenData(BaseModel):
    username: str | None = None


# JWT 相关配置
SECRET_KEY = "your_secret_key"  # 请替换为一个安全的密钥
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str, credentials_exception):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        print(f"Token payload: {payload}")  # 打印解码后的有效负载
        token_data = TokenData(username=username)
    except JWTError as e:
        print(f"JWT error: {e}")  # 打印 JWT 错误
        raise credentials_exception
    return token_data


app = FastAPI()
# 指定模板文件夹的路径
templates = Jinja2Templates(directory="templates")
# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头部
)
register_tortoise(
    app,
    db_url='sqlite://data/db.sqlite3',  # 修改数据库文件路径
    modules={'models': ['models']},
    generate_schemas=True,
    add_exception_handlers=True,
)

# 定义应用启动时的行为
@app.on_event("startup")
async def startup_event():
    print("Starting up...")
    await AdminUser.create_admin()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    print(f"Token received: {token}")  # 打印收到的令牌
    return verify_token(token, credentials_exception)


async def authenticate_user(username: str, password: str):
    user = await AdminUser.get_or_none(username=username)
    print(f"User found: {user is not None}, Username: {username}")
    if user and user.verify_password(password):
        print("Password verified")
        return user
    print("Authentication failed")
    return None




@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token}



# 创建一个 Pydantic 模型，用于序列化数据库模型
LotteryTicket_Pydantic = pydantic_model_creator(LotteryTicket, name="LotteryTicket")

@app.get("/tickets/", response_model=List[LotteryTicket_Pydantic])
async def get_tickets():
    return await LotteryTicket_Pydantic.from_queryset(LotteryTicket.all())



@app.post("/generate_ticket/")
async def generate_ticket(current_user: AdminUser = Security(get_current_user)):
    ticket_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    ticket = await LotteryTicket.create(ticket_code=ticket_code)
    return {"ticket_code": ticket.ticket_code}

@app.post("/submit_ticket/{ticket_code}")
async def submit_ticket(ticket_code: str):
    ticket = await LotteryTicket.get_or_none(ticket_code=ticket_code)
    if ticket is None:
        raise HTTPException(status_code=400, detail="Invalid ticket code")
    if ticket.used:
        # raise HTTPException(status_code=200, detail="Ticket already used")
        return {"result": "Ticket already used"}

    result = get_random_result()
    ticket.result = result

    if result != "再来一次":
        ticket.used = True  # 抽奖码使用完毕

    await ticket.save()
    return {"result": ticket.result}



@app.get("/admin/tickets/")
async def get_tickets(ticket_code: str = None, current_user: AdminUser = Security(get_current_user)):
    print("ticket_code:", ticket_code)
    if ticket_code:
        tickets = await LotteryTicket.filter(ticket_code__contains=ticket_code).all()
    else:
        tickets = await LotteryTicket.all()
    return tickets

# 使用 get_random_result 函数来生成抽奖结果
def get_random_result():
    prizes = ["谢谢参与", "300", "600", "900", "1500", "3000", "8800", "再来一次"]
    
    # 确保概率总和为 1
    # 示例概率，可以根据实际情况调整
    probabilities = [0.10, 0.36, 0.25, 0.10, 0.5, 0.03, 0.01, 0.10]  

    return random.choices(prizes, probabilities)[0]


@app.get("/login")
def get_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})
@app.get("/admin")
async def get_admin_dashboard(request: Request):
    # 这里可以添加逻辑来验证用户是否已登录
    return templates.TemplateResponse("admin_dashboard.html", {"request": request})
