import os

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database.db import get_db
from ..models.models import UploadedFile
from ..utils.helpers import safe_filename
from ..config.settings import settings

router = APIRouter(prefix="/files", tags=["files"])

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Keep uploads small and text-focused for now; raise this if you need more.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/upload")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()

    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File is larger than 10MB")

    stored_name = safe_filename(file.filename)
    file_path = os.path.join(settings.UPLOAD_DIR, stored_name)

    with open(file_path, "wb") as f:
        f.write(contents)

    record = UploadedFile(
        filename=file.filename or stored_name,
        stored_name=stored_name,
        content_type=file.content_type,
        size=len(contents),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "id": record.id,
        "filename": record.filename,
        "size": record.size,
        "content_type": record.content_type,
    }


@router.get("")
def list_files(db: Session = Depends(get_db)):
    files = db.query(UploadedFile).order_by(UploadedFile.uploaded_at.desc()).all()
    return [
        {
            "id": f.id,
            "filename": f.filename,
            "size": f.size,
            "content_type": f.content_type,
            "uploaded_at": f.uploaded_at.isoformat(),
        }
        for f in files
    ]


@router.get("/{file_id}/download")
def download_file(file_id: int, db: Session = Depends(get_db)):
    record = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = os.path.join(settings.UPLOAD_DIR, record.stored_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File missing on disk")

    return FileResponse(file_path, filename=record.filename)


@router.delete("/{file_id}")
def delete_file(file_id: int, db: Session = Depends(get_db)):
    record = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = os.path.join(settings.UPLOAD_DIR, record.stored_name)
    if os.path.exists(file_path):
        os.remove(file_path)

    db.delete(record)
    db.commit()
    return {"status": "deleted"}
