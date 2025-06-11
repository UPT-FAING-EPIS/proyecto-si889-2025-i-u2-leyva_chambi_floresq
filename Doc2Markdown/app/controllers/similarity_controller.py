from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from config.database import get_db
from app.models.document_model import Document
from app.models.user_model import User
from app.utils.plagiarism_detector import PlagiarismDetector
import re

router = APIRouter()

@router.get("/document-info/{document_id}")
async def get_document_info(document_id: int, db: Session = Depends(get_db)):
    """
    Obtiene la información básica de un documento para mostrar en el modal
    """
    document = db.query(Document).join(User).filter(
        Document.document_id == document_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    # Calcular estadísticas del contenido
    content = document.markdown_content or ""
    word_count = len(content.split())
    char_count = len(content)
    line_count = len(content.splitlines())
    
    return {
        "document_id": document.document_id,
        "title": document.title,
        "author": document.user.username,
        "author_email": document.user.email,
        "created_at": document.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": document.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        "version": document.version,
        "original_format": document.original_format,
        "statistics": {
            "word_count": word_count,
            "character_count": char_count,
            "line_count": line_count
        }
    }

@router.post("/analyze-similarities/{document_id}")
async def analyze_similarities(document_id: int, db: Session = Depends(get_db)):
    """
    Analiza las similitudes de un documento con todos los documentos de otros usuarios
    """
    # Obtener el documento objetivo
    target_document = db.query(Document).filter(
        Document.document_id == document_id
    ).first()
    
    if not target_document:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    # Obtener todos los documentos EXCEPTO los del mismo usuario
    other_documents = db.query(Document).join(User).filter(
        Document.user_id != target_document.user_id,
        Document.markdown_content.isnot(None),
        Document.markdown_content != ""
    ).all()
    
    if not other_documents:
        return {
            "message": "No se encontraron otros documentos para comparar",
            "target_document": {
                "id": target_document.document_id,
                "title": target_document.title
            },
            "comparisons": []
        }
    
    # Preparar datos para el detector de plagio
    documents_data = []
    
    # Agregar documento objetivo
    documents_data.append({
        "id": target_document.document_id,
        "title": target_document.title,
        "author": target_document.user.username,
        "content": target_document.markdown_content
    })
    
    # Agregar otros documentos
    for doc in other_documents:
        documents_data.append({
            "id": doc.document_id,
            "title": doc.title,
            "author": doc.user.username,
            "content": doc.markdown_content
        })
    
    # Usar el detector de plagio
    detector = PlagiarismDetector()
    similarity_results = detector.analyze_similarities(documents_data, target_document.document_id)
    
    return {
        "target_document": {
            "id": target_document.document_id,
            "title": target_document.title,
            "author": target_document.user.username
        },
        "total_comparisons": len(similarity_results),
        "comparisons": similarity_results
    }