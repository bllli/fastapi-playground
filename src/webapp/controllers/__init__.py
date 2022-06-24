from fastapi import APIRouter

from webapp.controllers.v10 import v10_router

__all__ = ['main_router']

main_router = APIRouter()
main_router.include_router(v10_router)
