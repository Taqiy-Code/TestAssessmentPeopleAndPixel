import json
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from typing import Literal

from app.schemas import MentionItem, MentionSearchFilter, Pagination
from app.utils import normalize_mention
from hashlib import sha256

router = APIRouter()

@router.post("/internal/mentions/bulk")
async def internal_bulk_ingest(request: Request, file: UploadFile = File(...)):
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
            title = normalized_mention.title if normalized_mention.title not in ["", None] else ""

            idempotency_key = f"{title.lower().strip()}|{normalized_mention.content.lower().strip()}"
                        
            records.append((
                normalized_mention.external_id,
                normalized_mention.source,
                normalized_mention.title,
                normalized_mention.content,
                normalized_mention.url,
                normalized_mention.author,
                normalized_mention.published_at,
                normalized_mention.engagement,
                sha256(idempotency_key.encode()).hexdigest()
            ))
        except Exception as e:
            not_processed.append(item)
            print(e)
            continue
            
    if not records:
        raise HTTPException(detail={
            "message": "No valid data to insert"
        }, status_code=status.HTTP_400_BAD_REQUEST)
        
    query = """
        WITH url_update AS (
            UPDATE mentions 
            SET engagement = GREATEST(mentions.engagement, $8),
                title = COALESCE(mentions.title, $3),
                content = COALESCE(mentions.content, $4),
                author = COALESCE(mentions.author, $6),
                published_at = COALESCE(mentions.published_at, $7)
            WHERE url = $5
            RETURNING id
        )
        INSERT INTO mentions (external_id, source, title, content, url, author, published_at, engagement, idempotency_key)
        SELECT $1, $2, $3, $4, $5, $6, $7, $8, $9
        WHERE NOT EXISTS (SELECT 1 FROM url_update)
        ON CONFLICT (idempotency_key) DO UPDATE SET 
            engagement = GREATEST(mentions.engagement, EXCLUDED.engagement), 
            title = COALESCE(mentions.title, EXCLUDED.title), 
            content = COALESCE(mentions.content, EXCLUDED.content),
            url = COALESCE(mentions.url, EXCLUDED.url),
            author = COALESCE(mentions.author, EXCLUDED.author),
            published_at = COALESCE(mentions.published_at, EXCLUDED.published_at);
    """
    
    pool = request.app.state.pool
    try:
        async with pool.acquire() as conn:
            await conn.executemany(query, records)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Internal Server Error")
        
    return JSONResponse(content={
        "message": "Bulk Import Completed",
        "data": {
            "processed": {
                "count": len(records),
                "inserted": jsonable_encoder(records)
            },
            "not_processed": {
                "count": len(not_processed),
                "data": jsonable_encoder(not_processed)
            }
        }
    }, status_code=status.HTTP_200_OK)

@router.get("/mentions")
async def search_mentions(request: Request, filter: MentionSearchFilter = Depends()):
    pool = request.app.state.pool

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
        print(e)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/mentions/stats")
async def mention_stats(request: Request, group_by: Literal["source", "day"]):
    pool = request.app.state.pool

    try:
        async with pool.acquire() as conn:
            if group_by == "source":
                query = """
                    SELECT source, COUNT(*) AS count
                    FROM mentions
                    GROUP BY source
                    ORDER BY count DESC
                """
            else:
                query = """
                    SELECT DATE_TRUNC('day', published_at) AS day, COUNT(*) AS count
                    FROM mentions
                    GROUP BY day
                    ORDER BY day DESC
                """
            
            query_result = await conn.fetch(query)

        if group_by == "source":
            return [{"source": row["source"], "count": row["count"]} for row in query_result]
        elif group_by == "day":
            return [{"day": row["day"], "count": row["count"]} for row in query_result]
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Internal Server Error")
