from fastapi import APIRouter

from webapp.controllers.v10.books import router as v10_books_router

__all__ = ['v10_router']

v10_router = APIRouter(prefix='/v1.0')
v10_router.include_router(v10_books_router)
