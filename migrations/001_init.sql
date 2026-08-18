CREATE TABLE mentions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  external_id TEXT NOT NULL,         
  source TEXT NOT NULL,              
  title TEXT,
  content TEXT NOT NULL,             
  url TEXT NOT NULL,
  author TEXT,
  published_at TIMESTAMPTZ,     
  engagement INT,     
  idempotency_key TEXT NOT NULL UNIQUE,    
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON mentions (source);
CREATE INDEX ON mentions (published_at);