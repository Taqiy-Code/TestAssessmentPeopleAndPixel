import json
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse
from asyncpg import Pool

from app.db import create_pool
from app.schemas import MentionItem, MentionSearchFilter, Pagination
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

@router.get("/mentions")
async def search_mentions(filter: MentionSearchFilter = Depends()):
    pool = await create_pool()

    try:
        async with pool.acquire() as conn:
            q_param = f"%{filter.q}%" if filter.q else None

            base_where = """
                WHERE 
                    (source = $1 OR $1 IS NULL) AND 
                    (published_at >= $2 OR $2 IS NULL) AND
                    (published_at <= $3 OR $3 IS NULL) AND
                    (title ILIKE $4 OR content ILIKE $4 OR $4 IS NULL)
            """

            count_query = f"SELECT COUNT(*) FROM mentions {base_where}"
            total_items = await conn.fetchval(
                count_query,
                filter.source, filter.from_date, filter.to, q_param
            )

            offset = (filter.page - 1) * filter.page_size
            data_query = f"""
                SELECT external_id, source, title, content, url, author, published_at, engagement
                FROM mentions
                {base_where}
                ORDER BY published_at DESC NULLS LAST, id DESC
                LIMIT $5 OFFSET $6
            """

            query_result = await conn.fetch(
                data_query,
                filter.source, filter.from_date, filter.to, q_param,
                filter.page_size, offset
            )

        mentions = [MentionItem(**dict(mention)) for mention in query_result]
        total_pages = (total_items + filter.page_size - 1) // filter.page_size if total_items > 0 else 0

        return Pagination(
            page=filter.page,
            page_size=filter.page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=filter.page < total_pages,
            has_prev=filter.page > 1,
            data=mentions
        )
    except Exception as e:
        print(str(e))
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await pool.close()

@router.get("/mentions/stats")
async def mention_stats(request):
    pass 
