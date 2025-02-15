import numpy as np

def monte_carlo_simulation(spot, mu, sigma, days, n_sims=10000):
    """蒙特卡洛价格路径模拟"""
    dt = 1/252
    paths = np.zeros((n_sims, days))
    paths[:,0] = spot
    
    for t in range(1, days):
        rand = np.random.normal(size=n_sims)
        paths[:,t] = paths[:,t-1] * np.exp((mu - 0.5*sigma**2)*dt + 
                      sigma*np.sqrt(dt)*rand)
    
    return paths

def calculate_itm_probability(paths, strike):
    """计算价内概率"""
    final_prices = paths[:,-1]
    return np.mean(final_prices > strike)