#!/usr/bin/env python3
"""Verifica i modelli nel database."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.db.supabase_client import get_supabase

client = get_supabase()

print("Pipeline eval models:")
result = client.table('llm_models').select('*').eq('use_case', 'pipeline_eval').execute()
for r in result.data:
    print(f"  {r['model_type']}: {r['model_name']}")

print("\nSupervisor models:")
result = client.table('llm_models').select('*').eq('use_case', 'supervisor').execute()
for r in result.data:
    print(f"  {r['model_type']}: {r['model_name']}")
