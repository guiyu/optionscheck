import numpy as np
from scipy.stats import norm

def calculate_greeks(option_type, strike, spot, t, iv, r=0.01):
    """
    计算单个期权的希腊字母值
    
    参数:
        option_type (str): 期权类型 ('call' 或 'put')
        strike (float): 行权价
        spot (float): 现货价格
        t (float): 剩余期限（天数）
        iv (float): 隐含波动率
        r (float): 无风险利率，默认1%
        
    返回:
        dict: 包含希腊字母值的字典
    """
    try:
        # 参数验证
        if not all(isinstance(x, (int, float)) for x in [strike, spot, t, iv]):
            return {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}
            
        # 确保参数为正数
        if any(x <= 0 for x in [strike, spot, iv]):
            return {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}
            
        # 将天数转换为年
        t_year = max(t / 365, 0.00001)  # 防止除零
        
        # 计算d1和d2
        sigma = max(iv, 0.0001)  # 防止波动率为0
        sqrt_t = np.sqrt(t_year)
        d1 = (np.log(spot/strike) + (r + 0.5 * sigma**2) * t_year) / (sigma * sqrt_t)
        d2 = d1 - sigma * sqrt_t
        
        # 计算标准正态分布的值
        nd1 = norm.cdf(d1)
        nd2 = norm.cdf(d2)
        pd1 = norm.pdf(d1)
        
        # 根据期权类型计算希腊字母
        if option_type.lower() == 'call':
            delta = nd1
            theta = (-spot * pd1 * sigma / (2 * sqrt_t) - 
                    r * strike * np.exp(-r * t_year) * nd2)
        else:
            delta = nd1 - 1
            theta = (-spot * pd1 * sigma / (2 * sqrt_t) + 
                    r * strike * np.exp(-r * t_year) * (1 - nd2))
        
        # 计算其他希腊字母
        gamma = pd1 / (spot * sigma * sqrt_t)
        vega = spot * sqrt_t * pd1 / 100  # 除以100使vega更易读
        
        # 检查结果是否为有效数值
        result = {
            'delta': delta,
            'gamma': gamma,
            'theta': theta,
            'vega': vega
        }
        
        # 处理无效值
        for key in result:
            if np.isnan(result[key]) or np.isinf(result[key]):
                result[key] = 0
                
        return result
        
    except Exception as e:
        print(f"计算希腊字母时发生错误: {str(e)}")
        return {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}