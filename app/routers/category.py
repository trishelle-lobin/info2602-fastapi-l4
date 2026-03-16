from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import select
from app.database import SessionDep
from app.models import *
from app.auth import encrypt_password, verify_password, create_access_token, AuthDep
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from fastapi import status
category_router = APIRouter(tags=["Category Management"])


@category_router.post("/category", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED )
async def create_cat(db:SessionDep, user:AuthDep, cat_data:CategoryCreate):
    category= Category(text=cat_data.text, user_id=user.id)
    try:
        db.add(category)
        db.commit()
        db.refresh(category)
        return category
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="An error occurred while creating an item",
        )

@category_router.post("/todo/{todo_id}/category/{cat_id}" )
async def add_cat(db:SessionDep, user:AuthDep, todo_id:int,cat_id:int):
    
    todo = db.exec(select(Todo).where(Todo.id==todo_id)).one_or_none()
    if not todo:
        raise HTTPException(
            status_code=404,
            detail="An error occurred while creating relation",
        )
    category = db.exec(select(Category).where(Category.id==cat_id)).one_or_none()
    if not category:
        raise HTTPException(
            status_code=404,
            detail="An error occurred while creating relation",
        )
    if (todo.user_id!=user.id):
          raise HTTPException(
            status_code=403,
            detail="An error occurred while creating relation",
        )
    if (category.user_id!=user.id):
         raise HTTPException(
            status_code=403,
            detail="An error occurred while creating relation",
        )
    todos = db.exec(select(TodoCategory).where((TodoCategory.todo_id==todo.id)&(TodoCategory.category_id==category.id))).one_or_none()
    
    if todos:
         return{"message":"Category already assigned to todo"}
   

    todos = TodoCategory(todo_id=todo.id,category_id=category.id)
    db.add(todos)
    db.commit()
    return{"message":"Category added successfully"}

@category_router.delete("/todo/{todo_id}/category/{cat_id}", status_code=status.HTTP_200_OK)
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
        return {"message":"Category deleted successfully"}
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="An error occurred while deleting an item",
        )
   
@category_router.get('/category/{cat_id}/todos', response_model=list[TodoResponse])
def get_todo_by_id(cat_id:int, db:SessionDep, user:AuthDep):
    cate = db.exec(select(Category).where(Category.user_id==user.id,Category.id==cat_id)).one_or_none()

    if not cate:
        raise HTTPException(
            status_code=403,
            detail="Error occurred, not authorized for this category",
        )
    todocat = db.exec(select(TodoCategory).where(TodoCategory.category_id==cat_id)).all()
    todos= []
    for data in todocat:
        todo=db.exec(select(Todo).where(Todo.id==data.todo_id,Todo.user_id==user.id )).one_or_none()
        if todo:
            todos.append(todo)
    return todos
  