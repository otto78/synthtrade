import math

class BudgetTooSmallError(Exception): pass

def calculate_quantity(budget_usdt: float, price: float, filters: dict) -> float:
    """
    TASK-088: Implementazione quantity_calculator.py
    """
    step_size = filters.get("stepSize", 1.0)
    min_qty = filters.get("minQty", 0.0)
    min_notional = filters.get("minNotional", 0.0)
    
    # 1. Calcolo quantità grezza
    raw_qty = budget_usdt / price
    
    # 2. Arrotondamento per difetto in base allo stepSize
    # Es: step_size 0.01, raw_qty 0.1234 -> 0.12
    precision = int(-math.log10(step_size)) if step_size < 1 else 0
    qty = math.floor(raw_qty / step_size) * step_size
    qty = round(qty, precision)
    
    # 3. Validazione minQty
    if qty < min_qty:
        raise BudgetTooSmallError(f"Quantity {qty} is below minQty {min_qty}")
        
    # 4. Validazione minNotional
    if qty * price < min_notional:
        raise BudgetTooSmallError(f"Notional {qty * price} is below minNotional {min_notional}")
        
    return qty
