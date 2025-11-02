from typing import Dict, Any, Optional

def extract_retail_price(data: Dict[str, Any]) -> Optional[float]:
    """Extract retail price from API response with validation."""
    try:
        flights_results = data.get("best_flights", [])
        if not flights_results:
            return None
        
        price = flights_results[0].get("price")
        if price is None:
            return None
            
        return float(price)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Failed to extract retail price: {str(e)}")
