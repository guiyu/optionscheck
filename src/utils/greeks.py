from py_vollib.black_scholes.greeks.analytical import (
    delta, gamma, theta, vega
)
import numpy as np

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
        t_year = max(t / 365, 0.00001)  # 防止除零，设置最小值
        
        # 标准化期权类型
        flag = 'c' if option_type.lower() == 'call' else 'p'
        
        # 标准化波动率
        iv = max(iv, 0.0001)  # 防止波动率为0
        
        try:
            # 计算希腊字母
            d = delta(flag, spot, strike, t_year, r, iv)
            g = gamma(flag, spot, strike, t_year, r, iv)
            v = vega(flag, spot, strike, t_year, r, iv)
            t = theta(flag, spot, strike, t_year, r, iv)
            
            # 检查结果是否为有效数值
            if any(np.isnan([d, g, v, t])) or any(np.isinf([d, g, v, t])):
                return {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}
                
            return {
                'delta': d,
                'gamma': g,
                'theta': t,
                'vega': v
            }
            
        except (ValueError, ZeroDivisionError) as e:
            return {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}
            
    except Exception as e:
        print(f"计算希腊字母时发生错误: {str(e)}")
        return {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}