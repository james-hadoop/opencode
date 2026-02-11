#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版：获取猪肉价格数据的示例脚本
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import time
import re

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_pig_price_data():
    """获取猪肉价格数据的简化版本"""
    
    # 尝试从农业农村部网站获取数据
    urls_to_try = [
        "https://www.agri.cn/sj/jgzs/2025/t20250102_8703329.htm",  # 2024年第52周
        "https://www.agri.cn/sj/jgzs/2025/t20250102_8703329.htm",  # 2025年第1周
        "https://capes.agri.cn/weixin/pigPrice",  # 日度指数
    ]
    
    all_data = []
    
    for url in urls_to_try:
        try:
            print(f"正在访问: {url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 查找表格数据
                tables = soup.find_all('table')
                
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 3:
                            text = ' '.join([cell.get_text().strip() for cell in cells])
                            
                            # 查找日期和价格
                            date_match = re.search(r'(\d{1,2})[月\.](\d{1,2})[日\.]', text)
                            price_match = re.search(r'(\d+\.?\d*)\s*元', text)
                            
                            if date_match and price_match:
                                month = int(date_match.group(1))
                                day = int(date_match.group(2))
                                price = float(price_match.group(1))
                                
                                # 尝试确定年份（默认2024年）
                                year = 2024 if '2024' in url else 2025
                                
                                try:
                                    date = datetime(year, month, day)
                                    
                                    all_data.append({
                                        '日期': date.strftime('%Y-%m-%d'),
                                        '猪肉价格': price,
                                        '单位': '元/公斤',
                                        '数据来源': url.split('/')[-1][:20]
                                    })
                                except:
                                    continue
                
                print(f"从 {url} 获取到 {len([d for d in all_data if d['数据来源'] in url])} 条数据")
            
            time.sleep(1)
            
        except Exception as e:
            print(f"访问 {url} 失败: {e}")
            continue
    
    return all_data

def create_sample_data():
    """创建示例数据（当无法获取真实数据时使用）"""
    sample_data = []
    
    # 创建从2023年1月1日到2025年1月1日的示例数据
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2025, 1, 1)
    
    current_date = start_date
    base_price = 25.0  # 基础价格
    
    while current_date <= end_date:
        # 添加一些随机波动
        seasonal_factor = 1.0 + 0.3 * (1 - (current_date.month - 1) / 6)  # 年内波动
        random_factor = 1.0 + (hash(str(current_date)) % 100 - 50) / 500  # 日波动
        
        price = base_price * seasonal_factor * random_factor
        price = round(price, 2)
        
        sample_data.append({
            '日期': current_date.strftime('%Y-%m-%d'),
            '猪肉价格': price,
            '单位': '元/公斤',
            '数据来源': '示例数据'
        })
        
        current_date += timedelta(days=1)
    
    return sample_data

def main():
    print("=" * 50)
    print("猪肉价格数据获取程序")
    print("=" * 50)
    
    # 尝试获取真实数据
    print("\n步骤1: 尝试从官方网站获取数据...")
    real_data = get_pig_price_data()
    
    if real_data:
        print(f"\n成功获取 {len(real_data)} 条真实数据")
        final_data = real_data
    else:
        print("\n无法从官方网站获取数据，使用示例数据...")
        final_data = create_sample_data()
        print(f"创建了 {len(final_data)} 条示例数据")
    
    # 保存到CSV文件
    print("\n步骤2: 保存数据到CSV文件...")
    
    if final_data:
        df = pd.DataFrame(final_data)
        
        # 按日期排序
        df = df.sort_values('日期')
        
        # 去重
        df = df.drop_duplicates(subset=['日期'], keep='first')
        
        # 保存
        output_file = 'pork_price_data.csv'
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print(f"数据已保存到: {output_file}")
        print(f"总记录数: {len(df)}")
        
        # 显示统计信息
        print("\n数据统计:")
        print(f"  - 日期范围: {df['日期'].min()} 至 {df['日期'].max()}")
        print(f"  - 猪肉价格范围: {df['猪肉价格'].min():.2f} - {df['猪肉价格'].max():.2f} 元/公斤")
        print(f"  - 平均价格: {df['猪肉价格'].mean():.2f} 元/公斤")
        
        # 显示前10条和后10条数据
        print("\n数据预览 (前10条):")
        print(df.head(10).to_string(index=False))
        
        print("\n数据预览 (后10条):")
        print(df.tail(10).to_string(index=False))
        
    else:
        print("没有数据可保存")

if __name__ == "__main__":
    main()
