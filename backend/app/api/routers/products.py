import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session, selectinload

from app.core.auth import get_current_user, get_request_user
from app.core.rate_limit import limiter
from app.models import SKU, Store, User, get_db
from app.schemas import CSVPreviewResponse, CSVUploadResponse, SKUResponse, StockUpdateRequest, StoreResponse
from app.services import CSVUploadService

router = APIRouter(dependencies=[Depends(get_current_user)])
public_router = APIRouter()


async def _read_csv_upload(file: UploadFile, request: Request) -> str:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be a .csv")
    content = await file.read()
    from app.config.settings import settings

    if len(content) > settings.MAX_UPLOAD_FILE_SIZE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File size must be 5MB or less")
    return content.decode("utf-8")


@router.get("/stores", response_model=list[StoreResponse])
@public_router.get("/stores", response_model=list[StoreResponse])
def list_stores(current_user: User = Depends(get_request_user), db: Session = Depends(get_db)):
    return db.query(Store).filter(Store.user_id == current_user.id).order_by(Store.created_at.desc()).all()


@router.get("/stores/{store_id}", response_model=StoreResponse)
@public_router.get("/stores/{store_id}", response_model=StoreResponse)
def get_store(store_id: str, current_user: User = Depends(get_request_user), db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.user_id == current_user.id, Store.store_id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store


@router.get("/stores/{store_id}/skus", response_model=list[SKUResponse])
@public_router.get("/stores/{store_id}/skus", response_model=list[SKUResponse])
def list_store_skus(store_id: str, current_user: User = Depends(get_request_user), db: Session = Depends(get_db)):
    store = db.query(Store).options(selectinload(Store.skus)).filter(Store.user_id == current_user.id, Store.store_id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store.skus


@router.post("/stores/{store_id}/update-stock")
def update_stock(store_id: str, updates: list[StockUpdateRequest], current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.user_id == current_user.id, Store.store_id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    sku_lookup = {
        sku.sku_id: sku
        for sku in db.query(SKU).filter(SKU.user_id == current_user.id, SKU.store_id == store.id, SKU.sku_id.in_([item.sku_id for item in updates])).all()
    }
    updated = 0
    for item in updates:
        sku = sku_lookup.get(item.sku_id)
        if sku:
            sku.current_stock = item.current_stock
            updated += 1
    db.commit()
    return {"updated": updated, "total": len(updates)}


@router.post("/upload-preview", response_model=CSVPreviewResponse)
@public_router.post("/upload-preview", response_model=CSVPreviewResponse)
@limiter.limit("10/minute")
async def upload_preview(
    request: Request,
    file: UploadFile = File(...),
    mapping: str | None = Form(default=None),
    current_user: User = Depends(get_request_user),
    db: Session = Depends(get_db),
):
    content = await _read_csv_upload(file, request)
    service = CSVUploadService(db)
    parsed_mapping = json.loads(mapping) if mapping else None
    return service.preview_csv(content, current_user, parsed_mapping)


@router.post("/upload-sales", response_model=CSVUploadResponse)
@public_router.post("/upload-sales", response_model=CSVUploadResponse)
@limiter.limit("5/minute")
async def upload_sales(
    request: Request,
    file: UploadFile = File(...),
    mapping: str | None = Form(default=None),
    excluded_rows: str | None = Form(default=None),
    current_user: User = Depends(get_request_user),
    db: Session = Depends(get_db),
):
    content = await _read_csv_upload(file, request)
    service = CSVUploadService(db)
    parsed_mapping = json.loads(mapping) if mapping else None
    parsed_excluded_rows = json.loads(excluded_rows) if excluded_rows else []
    return service.process_csv(content, current_user, parsed_mapping, parsed_excluded_rows)


__all__ = ["router", "public_router"]
