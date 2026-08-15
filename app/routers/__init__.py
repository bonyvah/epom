from app.routers.auth import router as auth_router
from app.routers.document import router as document_router
from app.routers.project import router as project_router

__all__ = ["auth_router", "document_router", "project_router"]
