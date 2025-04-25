from fastapi import FastAPI, Depends, HTTPException, Form, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from models import SessionLocal, Poll, Vote, User, Category, Admin
from schemas import UserCreate, UserOut, PollCreate, PollOut, CategoryCreate, CategoryOut, Token
from typing import Optional, List
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from collections import defaultdict
import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi import Body

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# Настройки CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Настройки авторизации
SECRET_KEY = "your-secret-key-here-1234567890"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Dependency для БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(db: Session, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def authenticate_admin(db: Session, username: str, password: str):
    admin = db.query(Admin).filter(Admin.username == username).first()
    if not admin or not verify_password(password, admin.hashed_password):
        return False
    return admin

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = {"sub": username}
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == token_data["sub"]).first()
    if user is None:
        admin = db.query(Admin).filter(Admin.username == token_data["sub"]).first()
        if admin is None:
            raise credentials_exception
        return admin
    
    return user

@app.post("/register/", response_model=UserOut)
def register_user(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    hashed_password = get_password_hash(password)
    db_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # Сначала пробуем аутентифицировать как пользователя
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        # Если не пользователь, пробуем как администратора
        admin = authenticate_admin(db, form_data.username, form_data.password)
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = admin
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/polls/", response_model=PollOut)
def create_poll(
    poll: PollCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not isinstance(current_user, Admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create polls"
        )
    
    if poll.category_id and not db.query(Category).filter(Category.id == poll.category_id).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category not found"
        )
    
    db_poll = Poll(
        question=poll.question,
        category_id=poll.category_id
    )
    db.add(db_poll)
    db.commit()
    db.refresh(db_poll)
    return db_poll

@app.get("/polls/", response_model=List[PollOut])
def read_polls(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Poll).offset(skip).limit(limit).all()

@app.post("/vote/")
def create_vote(
    vote_data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    poll_id = vote_data.get("poll_id")
    option = vote_data.get("option")
    poll = db.query(Poll).filter(Poll.id == poll_id).first()
    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Опрос не найден"
        )
    
    valid_options = ['За', 'Против', 'Не знаю']
    if option not in valid_options:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимый вариант. Используйте: {', '.join(valid_options)}"
        )
    
    existing_vote = db.query(Vote).filter(
        Vote.poll_id == poll_id,
        Vote.user_id == current_user.id
    ).first()
    
    if existing_vote:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Вы уже голосовали в этом опросе"
        )
    
    db_vote = Vote(
        poll_id=poll_id,
        option=option,
        user_id=current_user.id
    )
    db.add(db_vote)
    db.commit()
    
    votes = db.query(Vote).filter(Vote.poll_id == poll_id).all()
    results = defaultdict(int)
    for vote in votes:
        results[vote.option] += 1
    
    return {
        "message": "Голос учтен",
        "results": dict(results),
        "total_votes": sum(results.values())
    }

@app.get("/polls/category/{category_id}", response_model=List[PollOut])
def get_polls_by_category(category_id: int, db: Session = Depends(get_db)):
    return db.query(Poll).filter(Poll.category_id == category_id).all()

@app.get("/polls/{poll_id}/results")
def get_poll_results(poll_id: int, db: Session = Depends(get_db)):
    votes = db.query(Vote).filter(Vote.poll_id == poll_id).all()
    results = defaultdict(int)
    for vote in votes:
        results[vote.option] += 1
    return results

@app.get("/categories/", response_model=List[CategoryOut])
def read_categories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Category).offset(skip).limit(limit).all()

@app.get("/polls/results")
def get_all_polls_results(db: Session = Depends(get_db)):
    polls = db.query(Poll).all()
    results = {
        "questions": [],
        "votes": []
    }
    
    for poll in polls:
        votes = db.query(Vote).filter(Vote.poll_id == poll.id).all()
        vote_counts = defaultdict(int)
        for vote in votes:
            vote_counts[vote.option] += 1
        
        results["questions"].append(poll.question)
        results["votes"].append(sum(vote_counts.values()))
    
    return results

@app.get("/users/me", response_model=UserOut)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.post("/categories/", response_model=CategoryOut)
def create_category(
    category: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not isinstance(current_user, Admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create categories"
        )
    
    db_category = Category(**category.dict())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
#http://127.0.0.1:8000