from py_vollib.black_scholes.greeks.analytical import (
    delta, gamma, theta, vega
)

def calculate_greeks(option_type, strike, spot, t, iv, r=0.01):
    """计算单个期权的希腊值"""
    flag = 'c' if option_type == 'call' else 'p'
    t_year = t / 365
    
    return {
        'delta': delta(flag, spot, strike, t_year, r, iv),
        'gamma': gamma(flag, spot, strike, t_year, r, iv),
        'theta': theta(flag, spot, strike, t_year, r, iv),
        'vega': vega(flag, spot, strike, t_year, r, iv)
    }