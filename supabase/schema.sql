-- ============================================================
--  kkAgentic Support — Supabase schema (Postgres + pgvector)
--  Run this in the Supabase SQL editor.
--  NOTE: embedding dimension below (384) matches
--        sentence-transformers/all-MiniLM-L6-v2.
--        If you switch embedding models, change vector(384) AND
--        EMBEDDING_DIM in .env to match.
-- ============================================================

create extension if not exists vector;

-- ---- Projects: one row per project that has its own agent persona ----
create table if not exists projects (
    id          uuid primary key default gen_random_uuid(),
    key         text unique not null,          -- short slug, e.g. "billing-portal"
    name        text not null,                 -- display name
    description text not null,                  -- what this project is (used by the ROUTER)
    keywords    text[] default '{}',            -- routing hints
    persona     text default '',                -- extra system-prompt flavour for the ANSWER agent
    is_active   boolean default true,
    created_at  timestamptz default now()
);

-- ---- Document / FAQ chunks with embeddings ----
create table if not exists documents (
    id          uuid primary key default gen_random_uuid(),
    project_id  uuid not null references projects(id) on delete cascade,
    source      text,                           -- file name / URL the chunk came from
    title       text,
    content     text not null,                  -- the chunk text
    chunk_index int default 0,
    embedding   vector(384),
    metadata    jsonb default '{}'::jsonb,
    created_at  timestamptz default now()
);

create index if not exists documents_project_idx on documents(project_id);

-- Approximate nearest-neighbour index (cosine). Tune lists for your data size.
create index if not exists documents_embedding_idx
    on documents using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- ---- Conversation log (analytics + audit) ----
create table if not exists conversations (
    id                uuid primary key default gen_random_uuid(),
    channel           text,                     -- 'web' | 'telegram' | 'streamlit'
    user_ref          text,                     -- chat id / session id (no PII required)
    question          text not null,
    routed_project_id uuid references projects(id),
    routed_project_key text,
    confidence        real,
    answer            text,
    created_at        timestamptz default now()
);

create index if not exists conversations_created_idx on conversations(created_at desc);

-- ============================================================
--  Vector search RPC. Returns the best-matching chunks for a
--  project, ordered by cosine similarity.
-- ============================================================
create or replace function match_documents(
    query_embedding vector(384),
    p_project_id    uuid,
    match_count     int default 5
)
returns table (
    id         uuid,
    content    text,
    title      text,
    source     text,
    similarity float
)
language sql stable
as $$
    select
        d.id,
        d.content,
        d.title,
        d.source,
        1 - (d.embedding <=> query_embedding) as similarity
    from documents d
    where d.project_id = p_project_id
      and d.embedding is not null
    order by d.embedding <=> query_embedding
    limit match_count;
$$;

-- ============================================================
--  Row Level Security (optional but recommended)
--  Reads are public; writes go through the service-role key.
-- ============================================================
alter table projects      enable row level security;
alter table documents     enable row level security;
alter table conversations enable row level security;

drop policy if exists "public read projects"  on projects;
drop policy if exists "public read documents" on documents;

create policy "public read projects"  on projects      for select using (is_active);
create policy "public read documents" on documents     for select using (true);
-- conversations: no public select policy (insert handled by service role / backend).
