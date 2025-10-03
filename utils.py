from datetime import datetime, time, timedelta
import pytz
from typing import Dict, Optional, Tuple
import numpy as np

def format_currency(value: float, symbol: str = "$") -> str:
    """
    Formátuje číslo jako měnu
    """
    if value < 0:
        return f"-{symbol}{abs(value):,.2f}"
    return f"{symbol}{value:,.2f}"

def format_percentage(value: float, decimals: int = 1) -> str:
    """
    Formátuje číslo jako procento
    """
    return f"{value*100:.{decimals}f}%"

def get_market_status() -> Dict:
    """
    Zjistí aktuální stav trhu (otevřený/zavřený)
    """
    # Časová zóna New York (ET)
    et_tz = pytz.timezone('America/New_York')
    now_et = datetime.now(et_tz)
    
    # Market hours
    market_open = time(9, 30)
    market_close = time(16, 0)
    
    # Pre-market a after-hours
    premarket_open = time(4, 0)
    afterhours_close = time(20, 0)
    
    current_time = now_et.time()
    is_weekday = now_et.weekday() < 5  # Monday = 0, Friday = 4
    
    # Svátky (zjednodušená verze - v produkci použít holiday calendar)
    holidays = [
        datetime(2024, 1, 1),   # New Year's Day
        datetime(2024, 1, 15),  # MLK Day
        datetime(2024, 2, 19),  # Presidents Day
        datetime(2024, 3, 29),  # Good Friday
        datetime(2024, 5, 27),  # Memorial Day
        datetime(2024, 6, 19),  # Juneteenth
        datetime(2024, 7, 4),   # Independence Day
        datetime(2024, 9, 2),   # Labor Day
        datetime(2024, 11, 28), # Thanksgiving
        datetime(2024, 12, 25), # Christmas
    ]
    
    is_holiday = now_et.date() in [h.date() for h in holidays]
    
    # Status
    if not is_weekday or is_holiday:
        # Weekend nebo svátek
        next_open = get_next_market_open(now_et)
        time_to_open = next_open - now_et
        
        return {
            'is_open': False,
            'is_premarket': False,
            'is_afterhours': False,
            'status': 'Closed (Weekend/Holiday)',
            'current_time': now_et.strftime('%I:%M %p ET'),
            'time_to_open': format_timedelta(time_to_open),
            'time_to_close': 'N/A'
        }
    
    elif market_open <= current_time <= market_close:
        # Regular trading hours
        close_time = now_et.replace(hour=16, minute=0, second=0)
        time_to_close = close_time - now_et
        
        return {
            'is_open': True,
            'is_premarket': False,
            'is_afterhours': False,
            'status': '🟢 Market Open',
            'current_time': now_et.strftime('%I:%M %p ET'),
            'time_to_open': 'Now',
            'time_to_close': format_timedelta(time_to_close)
        }
    
    elif premarket_open <= current_time < market_open:
        # Pre-market
        open_time = now_et.replace(hour=9, minute=30, second=0)
        time_to_open = open_time - now_et
        
        return {
            'is_open': False,
            'is_premarket': True,
            'is_afterhours': False,
            'status': '🟡 Pre-Market',
            'current_time': now_et.strftime('%I:%M %p ET'),
            'time_to_open': format_timedelta(time_to_open),
            'time_to_close': 'N/A'
        }
    
    elif market_close < current_time <= afterhours_close:
        # After-hours
        next_open = get_next_market_open(now_et)
        time_to_open = next_open - now_et
        
        return {
            'is_open': False,
            'is_premarket': False,
            'is_afterhours': True,
            'status': '🟠 After-Hours',
            'current_time': now_et.strftime('%I:%M %p ET'),
            'time_to_open': format_timedelta(time_to_open),
            'time_to_close': 'N/A'
        }
    
    else:
        # Closed
        next_open = get_next_market_open(now_et)
        time_to_open = next_open - now_et
        
        return {
            'is_open': False,
            'is_premarket': False,
            'is_afterhours': False,
            'status': '🔴 Market Closed',
            'current_time': now_et.strftime('%I:%M %p ET'),
            'time_to_open': format_timedelta(time_to_open),
            'time_to_close': 'N/A'
        }

def get_next_market_open(current_time: datetime) -> datetime:
    """
    Vypočítá, kdy se trh příště otevře
    """
    et_tz = pytz.timezone('America/New_York')
    next_open = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
    
    # Pokud je po 9:30, posuň na další den
    if current_time.time() >= time(9, 30):
        next_open += timedelta(days=1)
    
    # Přeskoč víkendy
    while next_open.weekday() >= 5:  # Saturday = 5, Sunday = 6
        next_open += timedelta(days=1)
    
    return next_open

def format_timedelta(td: timedelta) -> str:
    """
    Formátuje timedelta do čitelného formátu
    """
    total_seconds = int(td.total_seconds())
    
    if total_seconds < 0:
        return "Expired"
    
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

def calculate_position_size(account_balance: float, risk_percentage: float,
                           stop_loss_points: float, point_value: float) -> int:
    """
    Vypočítá velikost pozice podle risk managementu
    """
    risk_amount = account_balance * (risk_percentage / 100)
    position_size = risk_amount / (stop_loss_points * point_value)
    return int(position_size)

def validate_trade_setup(entry: float, stop: float, target: float,
                        is_long: bool) -> Tuple[bool, Optional[str]]:
    """
    Validuje, zda je trade setup logický
    """
    if is_long:
        if stop >= entry:
            return False, "Stop loss must be below entry for long trades"
        if target <= entry:
            return False, "Target must be above entry for long trades"
    else:
        if stop <= entry:
            return False, "Stop loss must be above entry for short trades"
        if target >= entry:
            return False, "Target must be below entry for short trades"
    
    # Vypočítat RRR
    risk = abs(entry - stop)
    reward = abs(target - entry)
    
    if risk == 0:
        return False, "Risk cannot be zero"
    
    rrr = reward / risk
    
    if rrr < 1:
        return False, f"Risk/Reward ratio ({rrr:.2f}) is less than 1:1"
    
    return True, None

def generate_trade_id() -> str:
    """
    Generuje jedinečné ID pro trade
    """
    from uuid import uuid4
    return str(uuid4())[:8]

def calculate_kelly_criterion(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """
    Vypočítá optimální velikost pozice podle Kelly Criterion
    """
    if avg_loss == 0:
        return 0
    
    b = avg_win / avg_loss
    p = win_rate
    q = 1 - p
    
    kelly = (p * b - q) / b
    
    # Konzervativní Kelly (25% z plného Kelly)
    conservative_kelly = kelly * 0.25
    
    # Omezit na maximum 10% účtu
    return min(max(conservative_kelly, 0), 0.10)

def estimate_slippage(volume: int, order_size: int, spread: float) -> float:
    """
    Odhadne slippage pro daný order
    """
    # Základní slippage z bid-ask spreadu
    base_slippage = spread / 2
    
    # Dodatečný slippage podle velikosti orderu vzhledem k volume
    if volume > 0:
        size_impact = (order_size / volume) * spread * 10
    else:
        size_impact = spread
    
    total_slippage = base_slippage + size_impact
    
    # Maximum 1% slippage
    return min(total_slippage, 0.01)

def calculate_var(returns: list, confidence_level: float = 0.95) -> float:
    """
    Vypočítá Value at Risk
    """
    if not returns:
        return 0
    
    sorted_returns = sorted(returns)
    index = int((1 - confidence_level) * len(sorted_returns))
    
    return abs(sorted_returns[index]) if index < len(sorted_returns) else 0

def calculate_sharpe_ratio(returns: list, risk_free_rate: float = 0.05) -> float:
    """
    Vypočítá Sharpe Ratio
    """
    if not returns or len(returns) < 2:
        return 0
    
    returns_array = np.array(returns)
    excess_returns = returns_array - risk_free_rate / 252  # Daily risk-free rate
    
    if np.std(excess_returns) == 0:
        return 0
    
    return np.sqrt(252) * (np.mean(excess_returns) / np.std(excess_returns))
