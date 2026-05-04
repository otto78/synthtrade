#!/usr/bin/env python3
"""
[Nome Script] - Breve descrizione (1 frase).

Descrizione dettagliata di cosa fa questo script.
Spiega il contesto, quando usarlo, e cosa fa esattamente.

Input (CLI args):
  --param1: (string, required) Descrizione parametro 1
  --param2: (integer, required) Descrizione parametro 2
  --param3: (boolean, optional) Descrizione parametro 3 (default: False)

Output (JSON):
  Success: {"status": "success", "data": {...}}
  Error: {"status": "error", "reason": "...", "code": "ERROR_CODE"}

Env vars:
  ENV_VAR_1: Descrizione variabile d'ambiente 1
  ENV_VAR_2: Descrizione variabile d'ambiente 2

Examples:
  # Esempio 1: Caso d'uso base
  python script_name.py --param1="value1" --param2=123

  # Esempio 2: Con parametro opzionale
  python script_name.py --param1="value2" --param2=456 --param3

  # Esempio 3: Caso di errore
  python script_name.py --param1="" --param2=-1
  # Output: {"status": "error", "reason": "Invalid param1"}

Dependencies:
  - requests>=2.28.0
  - python-dotenv>=0.19.0

Author: [Nome]
Version: 1.0.0
Last modified: 2025-01-XX
"""

import argparse
import json
import logging
import os
import sys
from typing import Dict, Any, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurazione
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3


def validate_input(param1: str, param2: int) -> Optional[str]:
    """
    Valida gli input prima di procedere.
    
    Args:
        param1: Parametro 1 da validare
        param2: Parametro 2 da validare
    
    Returns:
        None se valido, stringa con errore se invalido
    """
    if not param1:
        return "param1 is required and cannot be empty"
    
    if param2 < 0:
        return "param2 must be a positive integer"
    
    # Aggiungi altre validazioni qui
    
    return None


def do_work(param1: str, param2: int, param3: bool = False) -> Dict[str, Any]:
    """
    Funzione che fa il lavoro concreto.
    
    Questa è la funzione principale che esegue l'operazione richiesta.
    Separata dal CLI per facilitare testing.
    
    Args:
        param1: Descrizione parametro 1
        param2: Descrizione parametro 2
        param3: Descrizione parametro 3 (default: False)
    
    Returns:
        Dict con risultato dell'operazione
    
    Raises:
        ValueError: Se input invalido
        RuntimeError: Se operazione fallisce
    """
    logger.info(f"Starting work with param1={param1}, param2={param2}, param3={param3}")
    
    # Esempio: Operazione concreta
    result = {
        "processed": True,
        "param1": param1,
        "param2": param2,
        "param3": param3,
        "output": f"Processed {param1} with value {param2}"
    }
    
    logger.info("Work completed successfully")
    return result


def main_function(param1: str, param2: int, param3: bool = False) -> Dict[str, Any]:
    """
    Funzione principale che coordina validazione ed esecuzione.
    
    Args:
        param1: Parametro 1
        param2: Parametro 2
        param3: Parametro 3 (default: False)
    
    Returns:
        Dict con status e data/reason
        {
            "status": "success" | "error",
            "data": {...} | None,
            "reason": str | None,
            "code": str | None
        }
    """
    try:
        # 1. Validazione input
        validation_error = validate_input(param1, param2)
        if validation_error:
            logger.error(f"Validation failed: {validation_error}")
            return {
                "status": "error",
                "reason": validation_error,
                "code": "INVALID_INPUT"
            }
        
        # 2. Verifica env vars necessarie
        env_var_1 = os.getenv("ENV_VAR_1")
        if not env_var_1:
            logger.error("ENV_VAR_1 not set")
            return {
                "status": "error",
                "reason": "ENV_VAR_1 environment variable not set",
                "code": "MISSING_ENV_VAR"
            }
        
        # 3. Esegui lavoro concreto
        result = do_work(param1, param2, param3)
        
        # 4. Ritorna successo
        return {
            "status": "success",
            "data": result
        }
    
    except ValueError as e:
        logger.error(f"Value error: {e}")
        return {
            "status": "error",
            "reason": str(e),
            "code": "VALUE_ERROR"
        }
    
    except RuntimeError as e:
        logger.error(f"Runtime error: {e}")
        return {
            "status": "error",
            "reason": str(e),
            "code": "RUNTIME_ERROR"
        }
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {
            "status": "error",
            "reason": f"Unexpected error: {str(e)}",
            "code": "UNEXPECTED_ERROR"
        }


def main():
    """Entry point CLI."""
    parser = argparse.ArgumentParser(
        description="[Descrizione script]",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --param1="value1" --param2=123
  %(prog)s --param1="value2" --param2=456 --param3
        """
    )
    
    parser.add_argument(
        "--param1",
        required=True,
        help="Descrizione parametro 1"
    )
    
    parser.add_argument(
        "--param2",
        type=int,
        required=True,
        help="Descrizione parametro 2"
    )
    
    parser.add_argument(
        "--param3",
        action="store_true",
        help="Descrizione parametro 3 (flag booleano)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Esegui funzione principale
    result = main_function(args.param1, args.param2, args.param3)
    
    # Output JSON
    print(json.dumps(result, indent=2))
    
    # Exit code
    exit_code = 0 if result["status"] == "success" else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
