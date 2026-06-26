#!/usr/bin/env python3
"""
Script di inizializzazione per i modelli LLM del supervisor (TASK-887)
Inserisce i valori default per use_case='supervisor' nel database.
"""

import sys
import os

# Aggiungi la directory app al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.db.supabase_client import get_supabase
from app.config import settings

def init_supervisor_models(force=False):
    """Inserisce i modelli default per use_case='supervisor'
    
    Args:
        force: Se True, sovrascrive senza chiedere conferma
    """
    
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        print("Errore: SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY non configurati")
        return False
    
    print(f"Connessione a Supabase: {settings.SUPABASE_URL}")
    client = get_supabase()
    
    # Prima verifica la struttura della tabella interrogando dati esistenti
    print("\nVerifica struttura tabella llm_models...")
    try:
        existing = client.table('llm_models').select('*').limit(1).execute()
        if existing.data:
            print("Colonne trovate (da record esistente):")
            columns = list(existing.data[0].keys())
            for col in columns:
                print(f"  - {col}")
            
            # Verifica la colonna del nome modello
            model_column = None
            for col in columns:
                if col in ['model', 'model_name', 'name', 'llm_model']:
                    model_column = col
                    break
            
            if not model_column:
                print("Errore: Impossibile trovare la colonna per il nome del modello")
                print("Colonne disponibili:", columns)
                return False
            
            print(f"\nUso colonna '{model_column}' per il nome del modello")
        else:
            print("Nessun record esistente, uso fallback colonna 'model'")
            model_column = 'model'
        
    except Exception as e:
        print(f"Errore durante verifica struttura: {e}")
        # Fallback: prova con 'model' come default
        model_column = 'model'
        print(f"Uso fallback colonna '{model_column}'")
    
    # Dati da inserire (usiamo ID completi OpenRouter per consistenza)
    supervisor_models = [
        {
            'use_case': 'supervisor',
            'model_type': 'cascade',
            'order_index': 0,
            model_column: 'anthropic/claude-haiku-4.5'
        },
        {
            'use_case': 'supervisor',
            'model_type': 'cascade',
            'order_index': 1,
            model_column: 'anthropic/claude-3.5-sonnet'
        },
        {
            'use_case': 'supervisor',
            'model_type': 'fallback',
            'order_index': None,
            model_column: 'anthropic/claude-haiku-4.5'
        }
    ]
    
    print("\nInserimento modelli supervisor:")
    for model_data in supervisor_models:
        print(f"  - {model_data['model_type']}: {model_data[model_column]}")
    
    try:
        # Verifica se esistono già dati per supervisor
        existing = client.table('llm_models').select('*').eq('use_case', 'supervisor').execute()
        
        if existing.data:
            print(f"\nTrovati {len(existing.data)} record esistenti per use_case='supervisor'")
            if not force:
                response = input("Vuoi sovrascrivere? (s/N): ")
                if response.lower() != 's':
                    print("Operazione annullata")
                    return False
            
            # Elimina i record esistenti
            print("Eliminazione record esistenti...")
            client.table('llm_models').delete().eq('use_case', 'supervisor').execute()
            print("Record eliminati, procedo con inserimento nuovi dati...")
        else:
            print("Nessun record esistente, procedo con inserimento...")
        
        # Inserisci i nuovi record
        print("\nInserimento nuovi record...")
        for model_data in supervisor_models:
            result = client.table('llm_models').insert(model_data).execute()
            if result.data:
                print(f"  [OK] {model_data['model_type']}: {model_data[model_column]}")
            else:
                print(f"  [ERRORE] Inserimento {model_data['model_type']}: {model_data[model_column]}")
                return False
        
        print("\nInizializzazione completata con successo!")
        print("\nConfigurazione supervisor:")
        print("  Cascade: anthropic/claude-haiku-4.5 -> anthropic/claude-3.5-sonnet")
        print("  Fallback: anthropic/claude-haiku-4.5")
        return True
        
    except Exception as e:
        print(f"\nErrore durante l'inserimento: {e}")
        return False

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Inizializza modelli supervisor nel database')
    parser.add_argument('--force', action='store_true', help='Sovrascrive senza chiedere conferma')
    args = parser.parse_args()
    success = init_supervisor_models(force=args.force)
    sys.exit(0 if success else 1)
