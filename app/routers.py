import json
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse
from asyncpg import Pool

from app.db import create_pool
from app.schemas import MentionItem
from app.utils import normalize_mention

router = APIRouter()

@router.post("/internal/mentions/bulk")
async def internal_bulk_ingest(file: UploadFile = File(...)):
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={
            "message" : "File must be JSON"
        })
    
    try:
        content = await file.read()
        data = json.loads(content)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={
            "message" : "Unable to parse JSON",
        })
        
    if not isinstance(data, list):
        data = [data]
        
    records = []
    not_processed = []
    for item in data:
        try:
            mention = MentionItem(**item)
            normalized_mention = normalize_mention(mention)
            dedup_key = f"{normalized_mention.external_id}-{normalized_mention.source.lower().strip()}"
                        
            records.append((
                normalized_mention.external_id,
                normalized_mention.source,
                normalized_mention.title,
                normalized_mention.content,
                normalized_mention.url,
                normalized_mention.author,
                normalized_mention.published_at,
                normalized_mention.engagement,
                dedup_key
            ))
        except Exception as e:
            not_processed.append(item)
            continue
            
    if not records:
        return {
            "message": "No valid data to insert"
        }
        
    query = """
        INSERT INTO mentions (external_id, source, title, content, url, author, published_at, engagement, idempotency_key)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ON CONFLICT (idempotency_key) DO NOTHING
    """
    
    pool = await create_pool()
    try:
        async with pool.acquire() as conn:
            await conn.executemany(query, records)
    finally:
        await pool.close()
        
    return JSONResponse(content={
        "message": "Bulk Import Completed",
        "count": {
            "processed": len(records),
            "not_processed": len(not_processed)
        }
    }, status_code=status.HTTP_200_OK)
