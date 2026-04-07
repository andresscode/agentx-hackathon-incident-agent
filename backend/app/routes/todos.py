from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models import Todo

router = APIRouter()


class TodoCreate(BaseModel):
    title: str


class TodoResponse(BaseModel):
    id: int
    title: str


@router.get("/api/todos", response_model=list[TodoResponse])
async def list_todos(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Todo).order_by(Todo.id))
    return result.scalars().all()


@router.post("/api/todos", response_model=TodoResponse, status_code=201)
async def create_todo(body: TodoCreate, session: AsyncSession = Depends(get_session)):
    todo = Todo(title=body.title)
    session.add(todo)
    await session.commit()
    await session.refresh(todo)
    return todo


@router.delete("/api/todos/{todo_id}", status_code=204)
async def delete_todo(todo_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Todo).where(Todo.id == todo_id))
    todo = result.scalar_one_or_none()
    if todo:
        await session.delete(todo)
        await session.commit()
