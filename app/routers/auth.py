from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import select
from app.database import SessionDep
from app.models import *
from app.auth import encrypt_password, verify_password, create_access_token, AuthDep
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from fastapi import status

auth_router = APIRouter(tags=["Authentication"])

@auth_router.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: SessionDep
) -> Token:
    user = db.exec(select(RegularUser).where(RegularUser.username == form_data.username)).one_or_none()
    if not user or not verify_password(plaintext_password=form_data.password, encrypted_password=user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(data={"sub": user.username, "role": user.role},)

    return Token(access_token=access_token, token_type="bearer")

@auth_router.get("/identify", response_model=UserResponse)
def get_user_by_id(db: SessionDep, user:AuthDep):
    return user

@auth_router.post('/signup', response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup_user(user_data: UserCreate, db:SessionDep):
  try:
    new_user = RegularUser(
        username=user_data.username, 
        email=user_data.email, 
        password=encrypt_password(user_data.password)
    )
    db.add(new_user)
    db.commit()
    return new_user
  except Exception:
    db.rollback()
    raise HTTPException(
                status_code=400,
                detail="Username or email already exists",
                headers={"WWW-Authenticate": "Bearer"},
            )
  
@auth_router.post("/category", response_model=CategoryResponse)
async def create_cat(db:SessionDep, user:AuthDep, cat_data:CategoryResponse):
    category = Category(text=cat_data.text, user_id=user.id)
    try:
        db.add(category)
        db.commit()
        db.refresh(category)
        return category
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="An error occurred while creating an item",
        )
    


@auth_router.post("/todo/{todo_id}/category/{cat_id}" )
async def create_cat(db:SessionDep, user:AuthDep, todo_id:int,cat_id:int):
    
    todo = db.exec(select(Todo).where(Todo.id==todo_id)).one_or_none()
    if not todo:
        raise HTTPException(
            status_code=404,
            detail="An error occurred while creating relation",
        )
    category = db.exec(select(Category).where(Category.id==cat_id)).one_or_none()
    if not category:
        raise HTTPException(
            status_code=403,
            detail="An error occurred while creating relation",
        )
    if (todo.user_id!=user.id):
          raise HTTPException(
            status_code=403,
            detail="An error occurred while creating relation",
        )
    if (category.user_id!=user.id):
         raise HTTPException(
            status_code=404,
            detail="An error occurred while creating relation",
        )
    todos = db.exec(select(TodoCategory).where((TodoCategory.todo_id==todo.id)&(TodoCategory.category_id==category.id))).one_or_none()
    
    if todos:
         return{"message":"Category already assigned to todo"}
   

    todos = TodoCategory(todo_id=todo.id,category_id=category.id)
    db.add(todos)
    db.commit()
    db.refresh(todos)
    return{"message":"Category added"}

@auth_router.delete("/todo/{todo_id}/category/{cat_id}", status_code=status.HTTP_200_OK)
def del_todo(todo_id: int, cat_id:int, db:SessionDep, user:AuthDep):

    todo = db.exec(select(Todo).where(Todo.id==todo_id)).one_or_none()

    if not todo:
        raise HTTPException(
            status_code=404,
            detail="Not found",
        )
    if todo.user_id!=user.id:
    
        raise HTTPException(
            status_code=403,
            detail="Error occurred",
        )
    category = db.exec(select(Category).where(Category.id==cat_id)).one_or_none()
    if not category:
        raise HTTPException(
            status_code=404,
            detail="Not found",
        )
    if category.user_id!=user.id:
    
        raise HTTPException(
            status_code=403,
            detail="Error occurred, not authorized for this category",
        )
    
    cat= db.exec(select(TodoCategory).where((TodoCategory.todo_id==todo.id)&(TodoCategory.category_id==category.id))).one_or_none()
    if cat is None:
         raise HTTPException(
            status_code=404,
            detail="Error occurred, no object",
        )
    
    try:
        db.delete(cat)
        db.commit()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="An error occurred while deleting an item",
        )
   
@auth_router.get('/category/{cat_id}/todos', response_model=list[TodoResponse])
def get_todo_by_id(cat_id:int, db:SessionDep, user:AuthDep):
    cate = db.exec(select(Category).where(Category.user_id==user.id)&(Category.id==cat_id)).one_or_none()

    if not cate:
        raise HTTPException(
            status_code=403,
            detail="Error occurred, not authorized for this category",
        )
    todocat = db.exec(select(TodoCategory).where(TodoCategory.category_id==cat_id)).all()
    todoid=[]
    for item in todocat:
        todoid.append(item.todo_id)
    todos = db.exec(select(Todo).where(Todo.id.in_(todoid))).all()
    return todos