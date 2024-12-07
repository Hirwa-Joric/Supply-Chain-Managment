from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .security import (
    create_access_token,
    get_current_user,
    verify_password,
    get_password_hash
)
from .logger import logger

# Create FastAPI app instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Setup CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Example of a protected endpoint
@app.get(f"{settings.API_V1_STR}/protected")
async def protected_route(current_user = Depends(get_current_user)):
    return {"message": "This is a protected route", "user": current_user}

# Example of pagination using settings
@app.get(f"{settings.API_V1_STR}/items")
async def get_items(
    page: int = 1,
    page_size: int = Depends(lambda: settings.DEFAULT_PAGE_SIZE),
    db: Session = Depends(get_db)
):
    if page_size > settings.MAX_PAGE_SIZE:
        page_size = settings.MAX_PAGE_SIZE
    
    skip = (page - 1) * page_size
    # Example query (replace with your actual model)
    # items = db.query(Item).offset(skip).limit(page_size).all()
    
    return {
        "page": page,
        "page_size": page_size,
        "items": []  # Replace with actual items
    }

# Example of file upload using settings
@app.post(f"{settings.API_V1_STR}/upload")
async def upload_file(file: UploadFile):
    if not any(file.filename.endswith(ext) for ext in settings.ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {settings.ALLOWED_EXTENSIONS}"
        )
    
    # Example file size check
    content = await file.read()
    if len(content) > settings.MAX_CONTENT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.MAX_CONTENT_LENGTH} bytes"
        )
    
    # Process file...
    logger.info(f"File uploaded: {file.filename}")
    return {"filename": file.filename}

# Example of environment-specific behavior
@app.get(f"{settings.API_V1_STR}/debug-info")
async def get_debug_info():
    if not settings.DEBUG:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debug information only available in development mode"
        )
    
    return {
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "database_url": settings.DATABASE_URL,
        "api_version": settings.VERSION
    }

# Startup event using settings
@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    if settings.DEBUG:
        logger.warning("Debug mode is enabled!")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"Shutting down {settings.PROJECT_NAME}")
