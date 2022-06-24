from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from webapp import main_router


def create_app():
    app = FastAPI()
    app.include_router(main_router)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):
        return JSONResponse({"status": 1, "message": "Validation failed", "errors": exc.errors()})

    return app


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('main.cmds.apiserver:create_app', host='localhost', port=8000, factory=True)
