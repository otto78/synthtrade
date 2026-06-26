-- Migration: add use_case column to llm_models
-- Permette configurazioni separate per use_case diversi (supervisor, pipeline_eval, etc.)
-- Data: 2026-06-26
-- TASK-887

-- Aggiungere colonna use_case con default 'pipeline_eval'
alter table llm_models 
add column if not exists use_case text not null default 'pipeline_eval';

-- Add check constraint for valid use cases
alter table llm_models 
add constraint llm_models_use_case_check 
check (use_case in ('pipeline_eval', 'supervisor'));

-- Update existing rows to have use_case='pipeline_eval' (per sicurezza)
update llm_models 
set use_case = 'pipeline_eval' 
where use_case is null or use_case = '';

-- Ricreare index per includere use_case
drop index if exists idx_llm_models_cascade_order;
create index idx_llm_models_cascade_order 
on llm_models (use_case, model_type, order_index);

-- Creare unique constraint per prevenire duplicati
create unique index if not exists idx_llm_models_unique 
on llm_models (use_case, model_type, order_index) 
where order_index is not null;
