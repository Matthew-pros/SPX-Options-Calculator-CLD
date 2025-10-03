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
        
        # Generovat strikes
        current_strike = start
        while (current_strike <= end if is_call else current_strike >= end):
            # Zaokrouhlit na nejbližší standardní strike
            rounded = self._round_to_standard_strike(current_strike)
            if rounded not in strikes:
                strikes.append(rounded)
            current_strike += step if is_call else -step
        
        return sorted(strikes)
    
    def _round_to_standard_strike(self, price: float) -> float:
        """
        Zaokrouhlí na standardní strike price
        """
        if price < 10:
            return round(price * 2) / 2  # 0.5 increments
        elif price < 100:
            return round(price)  # 1.0 increments
        elif price < 500:
            return round(price / 5) * 5  # 5.0 increments
        else:
            return round(price / 10) * 10  # 10.0 increments
    
    def find_spread_strategy(self, instrument: str, current_price: float,
                            entry: float, target: float, risk_amount: float,
                            is_call: bool = True, dte: int = 0, 
                            iv: float = 0.20) -> Dict:
        """
        Najde optimální vertical spread
        """
        # Šířka spreadu
        spread_width = abs(target - entry) / 2
        
        if is_call:
            long_strike = self._round_to_standard_strike(entry - spread_width/4)
            short_strike = self._round_to_standard_strike(target)
        else:
            long_strike = self._round_to_standard_strike(entry + spread_width/4)
            short_strike = self._round_to_standard_strike(target)
        
        T = max(dte / 365, 1/365/24)
        
        # Ceny opcí
        long_premium = self.calculator.black_scholes(
            S=entry, K=long_strike, T=T,
            r=self.calculator.risk_free_rate,
            sigma=iv, option_type='call' if is_call else 'put'
        )
        
        short_premium = self.calculator.black_scholes(
            S=entry, K=short_strike, T=T,
            r=self.calculator.risk_free_rate,
            sigma=iv, option_type='call' if is_call else 'put'
        )
        
        # Net debit
        net_debit = long_premium - short_premium
        
        if net_debit <= 0:
            return {'found': False, 'error': 'Invalid spread pricing'}
        
        # Počet spreadů
        contracts = min(
            int(risk_amount / (net_debit * 100)),
            self.max_contracts
        )
        
        if contracts == 0:
            return {'found': False, 'error': 'Insufficient capital'}
        
        # Max profit a loss
        max_profit = (abs(short_strike - long_strike) - net_debit) * contracts * 100
        max_loss = net_debit * contracts * 100
        
        return {
            'found': True,
            'type': 'Vertical Spread',
            'long_strike': long_strike,
            'short_strike': short_strike,
            'net_debit': round(net_debit, 2),
            'contracts': contracts,
            'max_profit': round(max_profit, 0),
            'max_loss': round(max_loss, 0),
            'rrr': round(max_profit / max_loss, 1) if max_loss > 0 else 0,
            'breakeven': long_strike + net_debit if is_call else long_strike - net_debit
        }
    
    def find_butterfly_strategy(self, instrument: str, current_price: float,
                               pin_target: float, risk_amount: float,
                               is_call: bool = True, dte: int = 0,
                               iv: float = 0.20) -> Dict:
        """
        Najde optimální butterfly spread pro "pin" strategie
        """
        # ATM strike (střed butterfly)
        atm_strike = self._round_to_standard_strike(pin_target)
        
        # Křídla (symetrická)
        wing_width = current_price * 0.02  # 2% šířka křídel
        lower_strike = self._round_to_standard_strike(atm_strike - wing_width)
        upper_strike = self._round_to_standard_strike(atm_strike + wing_width)
        
        T = max(dte / 365, 1/365/24)
        
        # Vypočítat prémie
        lower_premium = self.calculator.black_scholes(
            S=current_price, K=lower_strike, T=T,
            r=self.calculator.risk_free_rate,
            sigma=iv, option_type='call' if is_call else 'put'
        )
        
        atm_premium = self.calculator.black_scholes(
            S=current_price, K=atm_strike, T=T,
            r=self.calculator.risk_free_rate,
            sigma=iv, option_type='call' if is_call else 'put'
        )
        
        upper_premium = self.calculator.black_scholes(
            S=current_price, K=upper_strike, T=T,
            r=self.calculator.risk_free_rate,
            sigma=iv, option_type='call' if is_call else 'put'
        )
        
        # Net debit (long 1 lower, short 2 ATM, long 1 upper)
        net_debit = lower_premium - 2 * atm_premium + upper_premium
        
        if net_debit <= 0:
            return {'found': False, 'error': 'Butterfly yields credit (check inputs)'}
        
        # Počet butterfly spreadů
        contracts = min(
            int(risk_amount / (net_debit * 100)),
            self.max_contracts
        )
        
        if contracts == 0:
            return {'found': False, 'error': 'Insufficient capital for butterfly'}
        
        # Max profit (při pin na ATM strike)
        max_profit = (atm_strike - lower_strike - net_debit) * contracts * 100
        max_loss = net_debit * contracts * 100
        
        return {
            'found': True,
            'type': 'Butterfly Spread',
            'lower_strike': lower_strike,
            'atm_strike': atm_strike,
            'upper_strike': upper_strike,
            'net_debit': round(net_debit, 2),
            'contracts': contracts,
            'max_profit': round(max_profit, 0),
            'max_loss': round(max_loss, 0),
            'rrr': round(max_profit / max_loss, 1) if max_loss > 0 else 0,
            'pin_target': atm_strike,
            'profit_range': f"${lower_strike + net_debit:.2f} - ${upper_strike - net_debit:.2f}"
        }
    
    def analyze_multiple_strategies(self, **kwargs) -> pd.DataFrame:
        """
        Porovná více strategií najednou
        """
        strategies = []
        
        # Single option
        single = self.find_best_strike(**kwargs)
        if single['found']:
            strategies.append({
                'Strategy': 'Single Option',
                'Max Profit': single['max_profit'],
                'Max Loss': single['total_risk'],
                'RRR': single['rrr'],
                'Probability': f"{single['probability']:.1%}",
                'Contracts': single['contracts']
            })
        
        # Vertical spread
        spread = self.find_spread_strategy(**kwargs)
        if spread['found']:
            strategies.append({
                'Strategy': 'Vertical Spread',
                'Max Profit': spread['max_profit'],
                'Max Loss': spread['max_loss'],
                'RRR': spread['rrr'],
                'Probability': 'N/A',
                'Contracts': spread['contracts']
            })
        
        # Butterfly (jen pokud máme pin target)
        if 'pin_target' in kwargs:
            butterfly = self.find_butterfly_strategy(
                pin_target=kwargs['pin_target'],
                **{k: v for k, v in kwargs.items() if k != 'pin_target'}
            )
            if butterfly['found']:
                strategies.append({
                    'Strategy': 'Butterfly',
                    'Max Profit': butterfly['max_profit'],
                    'Max Loss': butterfly['max_loss'],
                    'RRR': butterfly['rrr'],
                    'Probability': 'Pin-based',
                    'Contracts': butterfly['contracts']
                })
        
        return pd.DataFrame(strategies)
