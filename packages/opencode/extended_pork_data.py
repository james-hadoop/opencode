#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扩展的猪肉价格数据获取脚本 - 覆盖近3年数据
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

def generate_urls_for_year(year):
    """生成指定年份的周报URL列表"""
    urls = []
    
    if year == 2025:
        weeks = [46, 45, 42, 41, 40, 39, 38, 37, 36, 35, 34, 33, 32, 31, 30]
        for week in weeks:
            urls.append((f"https://www.agri.cn/sj/jgzs/{year}/t{year}{week:02d}/index.htm", f"{year}年第{week}周"))
            # 也尝试其他可能的URL格式
            urls.append((f"https://www.agri.cn/sj/jgzs/{year}/t{year}{week:02d}_{hash(str(week)) % 100000:05d}.htm", f"{year}年第{week}周"))
    
    elif year == 2024:
        weeks = list(range(1, 53))  # 1-52周
        for week in weeks:
            urls.append((f"https://www.agri.cn/sj/jgzs/{year}/t{year}{week:02d}/index.htm", f"{year}年第{week}周"))
            urls.append((f"https://www.agri.cn/sj/jgzs/{year}/t{year}0{week if week < 10 else week}01_0000000.htm", f"{year}年第{week}周"))
    
    elif year == 2023:
        weeks = list(range(1, 53))
        for week in weeks:
            urls.append((f"https://www.agri.cn/sj/jgzs/{year}/t{year}{week:02d}/index.htm", f"{year}年第{week}周"))
            urls.append((f"https://www.agri.cn/sj/jgzs/{year}/t{year}0{week if week < 10 else week}01_0000000.htm", f"{year}年第{week}周"))
    
    return urls

def fetch_data_for_year(year):
    """获取指定年份的数据"""
    year_data = []
    
    urls = generate_urls_for_year(year)
    
    print(f"\n正在获取 {year} 年的数据，共 {len(urls)} 个URL...")
    
    for url, week_name in urls:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            
            if response.status_code == 200:
                table_data = extract_pig_price_data(response.content, url)
                
                if table_data:
                    year_data.extend(table_data)
                    print(f"  ✓ {week_name}: 获取 {len(table_data)} 条数据")
                    continue  # 成功获取，跳过备用URL
            
            # 短暂延迟
            import time
            time.sleep(0.3)
            
        except Exception as e:
            continue
    
    return year_data

def create_complete_timeseries(all_data):
    """创建完整的时间序列数据"""
    if not all_data:
        return []
    
    # 创建DataFrame
    df = pd.DataFrame(all_data)
    
    # 筛选全国数据
    national_data = df[df['地区'].isin(['16省', '总指数', '全国'])].copy()
    
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
    print("扩展版猪肉价格数据获取程序")
    print("目标：获取全国近3年每天的猪肉价格数据")
    print("数据来源：农业农村部瘦肉型白条猪肉出厂价格监测周报")
    print("=" * 70)
    
    all_data = []
    
    # 获取2023-2025年的数据
    for year in [2025, 2024, 2023]:
        print(f"\n{'='*50}")
        print(f"正在处理 {year} 年的数据...")
        year_data = fetch_data_for_year(year)
        
        if year_data:
            all_data.extend(year_data)
            print(f"  {year}年共获取 {len(year_data)} 条数据")
    
    if all_data:
        print(f"\n总共获取到 {len(all_data)} 条原始数据")
        
        # 生成完整时间序列
        print("\n正在生成完整的日度时间序列...")
        complete_data = create_complete_timeseries(all_data)
        
        if complete_data:
            # 保存数据
            df = pd.DataFrame(complete_data)
            df = df.sort_values('日期')
            
            output_file = 'pork_price_national_2023_2025.csv'
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
            
            print(f"\n数据预览 (后20条):")
            print(df.tail(20).to_string(index=False))
            
            print(f"\n✓ 程序执行成功！")
        else:
            print("\n✗ 无法生成完整时间序列")
    else:
        print("\n✗ 无法获取任何数据")

if __name__ == "__main__":
    main()
