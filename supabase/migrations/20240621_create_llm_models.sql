-- Migration: create table llm_models
-- This migration creates the table used to store the LLM cascade and fallback models.
-- The table is expected by `LLMModelRepository` in the backend.

create extension if not exists "uuid-ossp";  -- ensure uuid generation support

create table if not exists llm_models (
    id uuid primary key default uuid_generate_v4(),
    model_type text not null check (model_type in ('cascade', 'fallback')),
    order_index int,  -- only used for cascade models to preserve order
    model_name text not null,
    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone default now()
);

-- Index to quickly fetch cascade models ordered by order_index
create index if not exists idx_llm_models_cascade_order on llm_models (model_type, order_index);

-- Trigger to update `updated_at` on row modification
create or replace function llm_models_set_timestamp()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create trigger trg_llm_models_timestamp
before update on llm_models
for each row execute function llm_models_set_timestamp();
