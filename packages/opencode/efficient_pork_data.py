#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高效的猪肉价格数据获取脚本 - 重点获取可用数据
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import re

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def extract_pig_price_data(html_content, url):
    """从HTML中提取猪肉价格数据"""
    data = []
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 从URL中提取年份
    year_match = re.search(r'/(\d{4})/', url)
    year = int(year_match.group(1)) if year_match else 2025
    
    # 查找所有表格
    tables = soup.find_all('table', class_='MsoNormalTable')
    
    for table in tables:
        try:
            rows = table.find_all('tr')
            
            if len(rows) < 2:
                continue
            
            # 获取表头行（日期）
            header_row = rows[0]
            header_cells = header_row.find_all(['td', 'th'])
            
            # 提取日期
            dates = []
            for cell in header_cells[1:-1]:
                cell_text = cell.get_text().strip()
                date_match = re.search(r'(\d{1,2})[月\.\-](\d{1,2})[日\.\-]?', cell_text)
                if date_match:
                    month = int(date_match.group(1))
                    day = int(date_match.group(2))
                    dates.append((month, day))
            
            if not dates:
                continue
            
            # 处理数据行
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 3:
                    continue
                
                region = cells[0].get_text().strip()
                
                for i, date_tuple in enumerate(dates):
                    if i + 1 < len(cells):
                        cell_text = cells[i + 1].get_text().strip()
                        price_match = re.search(r'(\d+\.?\d*)', cell_text)
                        
                        if price_match:
                            price = float(price_match.group(1))
                            month, day = date_tuple
                            
                            try:
                                date = datetime(year, month, day)
                                
                                data.append({
                                    '日期': date.strftime('%Y-%m-%d'),
                                    '地区': region,
                                    '猪肉价格': price,
                                    '单位': '元/公斤'
                                })
                            except:
                                continue
        
        except Exception as e:
            continue
    
    return data

# 已知的可用URL列表（基于搜索结果）
KNOWN_URLS = [
    # 2025年
    ("https://www.agri.cn/sj/jgzs/202511/t20251117_8786530.htm", "2025年第46周"),
    ("https://www.agri.cn/sj/jgzs/202511/t20251111_8784970.htm", "2025年第45周"),
    ("https://www.agri.cn/sj/jgzs/202510/t20251027_8780347.htm", "2025年第42周"),
    ("https://www.agri.cn/sj/jgzs/202510/t20251021_6478326.htm", "2025年第41周"),
    ("https://www.agri.cn/sj/jgzs/202510/t20251014_6478101.htm", "2025年第40周"),
    ("https://www.agri.cn/sj/jgzs/202510/t20251011_6478048.htm", "2025年第39周"),
    
    # 2024年12月-2025年1月
    ("https://www.agri.cn/sj/jgzs/202501/t20250102_8703329.htm", "2024年第52周"),
    ("https://www.agri.cn/sj/jgzs/202412/t20241225_8701486.htm", "2024年第51周"),
    ("https://www.agri.cn/sj/jgzs/202412/t20241218_8699826.htm", "2024年第50周"),
    ("https://www.agri.cn/sj/jgzs/202412/t20241211_8697442.htm", "2024年第49周"),
    ("https://www.agri.cn/sj/jgzs/202412/t20241204_8695069.htm", "2024年第48周"),
]

def fetch_known_urls():
    """获取已知URL的数据"""
    all_data = []
    
    print("正在从已知URL获取数据...")
    
    for url, week_name in KNOWN_URLS:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            
            if response.status_code == 200:
                table_data = extract_pig_price_data(response.content, url)
                
                if table_data:
                    all_data.extend(table_data)
                    print(f"  ✓ {week_name}: 获取 {len(table_data)} 条数据")
            
            import time
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  ✗ {week_name}: 获取失败")
            continue
    
    return all_data

def create_complete_timeseries(all_data):
    """创建完整的时间序列数据"""
    if not all_data:
        return []
    
    # 创建DataFrame
    df = pd.DataFrame(all_data)
    
    # 筛选全国数据（16省）
    national_data = df[df['地区'].isin(['16省'])].copy()
    
    if national_data.empty:
        # 使用平均值
        df['日期'] = pd.to_datetime(df['日期'])
        national_data = df.groupby('日期').agg({
            '猪肉价格': 'mean',
            '单位': 'first'
        }).reset_index()
        national_data['地区'] = '全国平均'
    else:
        national_data = national_data[['日期', '猪肉价格', '单位', '地区']].copy()
    
    # 按日期排序并去重
    national_data['日期'] = pd.to_datetime(national_data['日期'])
    national_data = national_data.sort_values('日期')
    national_data = national_data.drop_duplicates(subset=['日期'], keep='first')
    
    # 填充缺失日期
    if len(national_data) > 1:
        min_date = national_data['日期'].min()
        max_date = national_data['日期'].max()
        full_date_range = pd.date_range(start=min_date, end=max_date, freq='D')
        
        full_df = pd.DataFrame({'日期': full_date_range})
        national_data = full_df.merge(national_data, on='日期', how='left')
        
        # 线性插值
        national_data['猪肉价格'] = national_data['猪肉价格'].interpolate(method='linear')
        national_data['猪肉价格'] = national_data['猪肉价格'].ffill().bfill()
        national_data['单位'] = national_data['单位'].fillna('元/公斤')
        national_data['地区'] = national_data['地区'].fillna('全国平均')
    
    national_data['日期'] = national_data['日期'].dt.strftime('%Y-%m-%d')
    
    return national_data.to_dict('records')

def main():
    print("=" * 70)
    print("高效版猪肉价格数据获取程序")
    print("目标：获取全国猪肉价格日度数据")
    print("数据来源：农业农村部瘦肉型白条猪肉出厂价格监测周报")
    print("=" * 70)
    
    # 获取数据
    all_data = fetch_known_urls()
    
    if all_data:
        print(f"\n总共获取到 {len(all_data)} 条原始数据")
        
        # 生成完整时间序列
        print("\n正在生成完整的日度时间序列...")
        complete_data = create_complete_timeseries(all_data)
        
        if complete_data:
            # 保存数据
            df = pd.DataFrame(complete_data)
            df = df.sort_values('日期')
            
            output_file = 'pork_price_national_daily.csv'
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            
            print(f"\n✓ 数据已保存到: {output_file}")
            print(f"✓ 最终数据量: {len(df)} 条")
            
            # 显示统计信息
            print(f"\n数据统计:")
            print(f"  - 日期范围: {df['日期'].min()} 至 {df['日期'].max()}")
            print(f"  - 价格范围: {df['猪肉价格'].min():.2f} - {df['猪肉价格'].max():.2f} 元/公斤")
            print(f"  - 平均价格: {df['猪肉价格'].mean():.2f} 元/公斤")
            print(f"  - 标准差: {df['猪肉价格'].std():.2f} 元/公斤")
            
            # 显示数据预览
            print(f"\n数据预览 (前20条):")
            print(df.head(20).to_string(index=False))
            
            print(f"\n✓ 程序执行成功！")
        else:
            print("\n✗ 无法生成完整时间序列")
    else:
        print("\n✗ 无法获取任何数据")

if __name__ == "__main__":
    main()
