import numpy as np
from typing import Dict, Optional, List, Tuple
from calculator import OptionsCalculator
from scipy.optimize import minimize_scalar
import pandas as pd

class OptionFinder:
    """
    Najde optimální opční strategii podle zadaných parametrů
    """
    
    def __init__(self):
        self.calculator = OptionsCalculator()
        self.min_probability = 0.25  # Minimální pravděpodobnost úspěchu
        self.max_contracts = 100     # Maximální počet kontraktů
        
    def find_best_strike(self, instrument: str, current_price: float, entry: float,
                        target: float, stop: float, risk_amount: float,
                        is_call: bool = True, dte: int = 0, iv: float = 0.20) -> Dict:
        """
        Najde nejlepší strike pro daný setup
        """
        # Základní validace
        if risk_amount <= 0 or current_price <= 0:
            return {'found': False, 'error': 'Invalid parameters'}
        
        # Čas do expirace v letech
        T = max(dte / 365, 1/365/24)  # Minimálně 1 hodina pro 0DTE
        
        # Určit rozsah strikes k analýze
        strikes = self._generate_strike_candidates(current_price, target, stop, is_call)
        
        best_option = None
        best_score = -float('inf')
        
        for strike in strikes:
            # Vypočítat cenu opce při vstupu
            option_price = self.calculator.black_scholes(
                S=entry,
                K=strike,
                T=T,
                r=self.calculator.risk_free_rate,
                sigma=iv,
                option_type='call' if is_call else 'put'
            )
            
            if option_price <= 0 or option_price * 100 > risk_amount:
                continue
            
            # Počet kontraktů
            contracts = min(
                int(risk_amount / (option_price * 100)),
                self.max_contracts
            )
            
            if contracts == 0:
                continue
            
            # Skutečný risk
            actual_risk = contracts * option_price * 100
            
            # Vypočítat hodnotu při targetu
            target_value = self.calculator.black_scholes(
                S=target,
                K=strike,
                T=T * 0.5,  # Předpokládáme dosažení v polovině času
                r=self.calculator.risk_free_rate,
                sigma=iv,
                option_type='call' if is_call else 'put'
            )
            
            # Potenciální profit
            max_profit = contracts * (target_value - option_price) * 100
            
            # Break-even
            breakeven = self.calculator.calculate_breakeven(strike, option_price, is_call)
            
            # Pravděpodobnost úspěchu
            probability = self.calculator.calculate_probability_of_profit(
                current_price=entry,
                break_even=breakeven,
                dte=dte,
                iv=iv,
                is_bullish=is_call
            )
            
            # Score = (profit/risk * probability) - distance penalty
            if actual_risk > 0 and probability >= self.min_probability:
                rrr = max_profit / actual_risk
                distance_penalty = abs(strike - entry) / entry * 10  # Penalizace vzdálených strikes
                score = (rrr * probability) - distance_penalty
                
                if score > best_score:
                    best_score = score
                    best_option = {
                        'found': True,
                        'strike': strike,
                        'entry_price': round(option_price, 2),
                        'target_price': round(target_value, 2),
                        'contracts': contracts,
                        'total_risk': round(actual_risk, 0),
                        'max_profit': round(max_profit, 0),
                        'breakeven': round(breakeven, 2),
                        'probability': probability,
                        'rrr': round(rrr, 1),
                        'score': score,
                        'prob_loss': 1 - probability
                    }
        
        if best_option is None:
            return {'found': False, 'error': 'No suitable option found'}
        
        return best_option
    
    def _generate_strike_candidates(self, current: float, target: float, 
                                   stop: float, is_call: bool) -> List[float]:
        """
        Generuje kandidáty na strikes
        """
        strikes = []
        
        if is_call:
            # Pro call: strikes od deep ITM po mírně OTM
            start = current * 0.95  # 5% ITM
            end = target           # Do targetu
            step = 1 if current < 100 else 5 if current < 1000 else 10
        else:
            # Pro put: strikes od mírně OTM po deep ITM
            start = target         # Od targetu
            end = current * 1.05   # 5% ITM
            step = 1 if current < 100 else 5 if current < 1000 else 10
        
        #
