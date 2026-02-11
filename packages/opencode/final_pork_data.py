#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从农业农村部周报中完整提取猪肉价格数据
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
    
    print(f"  找到 {len(tables)} 个表格")
    
    for table_idx, table in enumerate(tables):
        try:
            rows = table.find_all('tr')
            
            if len(rows) < 2:
                continue
            
            # 获取表头行（日期）
            header_row = rows[0]
            header_cells = header_row.find_all(['td', 'th'])
            
            # 提取日期（除了第一列和最后一列）
            dates = []
            for cell in header_cells[1:-1]:  # 跳过第一列和最后一列
                cell_text = cell.get_text().strip()
                date_match = re.search(r'(\d{1,2})[月\.\-](\d{1,2})[日\.\-]?', cell_text)
                if date_match:
                    month = int(date_match.group(1))
                    day = int(date_match.group(2))
                    dates.append((month, day))
            
            if not dates:
                continue
            
            # 处理数据行
            for row in rows[1:]:  # 跳过表头
                cells = row.find_all(['td', 'th'])
                if len(cells) < 3:
                    continue
                
                # 获取地区名称（第一列）
                region = cells[0].get_text().strip()
                
                # 获取价格数据
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
                                    '单位': '元/公斤',
                                    '来源': f'第{table_idx + 1}个表格'
                                })
                            except:
                                continue
        
        except Exception as e:
            print(f"  解析表格 {table_idx + 1} 失败: {e}")
            continue
    
    return data

def fetch_and_process():
    """获取并处理所有数据"""
    
    # 要访问的URL列表
    urls_info = [
        ("https://www.agri.cn/sj/jgzs/202511/t20251117_8786530.htm", "2025年第46周"),
        ("https://www.agri.cn/sj/jgzs/202511/t20251111_8784970.htm", "2025年第45周"),
        ("https://www.agri.cn/sj/jgzs/202510/t20251027_8780347.htm", "2025年第42周"),
        ("https://www.agri.cn/sj/jgzs/202501/t20250102_8703329.htm", "2024年第52周"),
        ("https://www.agri.cn/sj/jgzs/202412/t20241225_8701486.htm", "2024年第51周"),
    ]
    
    all_data = []
    
    for url, week_name in urls_info:
        print(f"\n正在处理 {week_name}: {url}")
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            }
            
            response = requests.get(url, headers=headers, timeout=15, verify=False)
            
            if response.status_code == 200:
                table_data = extract_pig_price_data(response.content, url)
                
                if table_data:
                    all_data.extend(table_data)
                    print(f"  成功提取 {len(table_data)} 条数据")
                else:
                    print(f"  未能提取到数据")
            else:
                print(f"  获取页面失败，HTTP状态码: {response.status_code}")
            
            # 暂停一下
            import time
            time.sleep(1)
            
        except Exception as e:
            print(f"  处理失败: {e}")
            continue
    
    return all_data

def generate_full_timeseries(data):
    """生成完整的日度时间序列数据"""
    if not data:
        return data
    
    # 创建DataFrame
    df = pd.DataFrame(data)
    
    # 筛选全国数据（地区为"16省"或"总指数"等）
    national_data = df[df['地区'].isin(['16省', '总指数', '全国'])]
    
    if national_data.empty:
        # 如果没有全国数据，使用所有数据的平均值
        df['日期'] = pd.to_datetime(df['日期'])
        national_data = df.groupby('日期').agg({
            '猪肉价格': 'mean',
            '单位': 'first',
            '地区': lambda x: '全国平均'
        }).reset_index()
        national_data['日期'] = national_data['日期'].dt.strftime('%Y-%m-%d')
    else:
        national_data = national_data[['日期', '猪肉价格', '单位', '地区']].copy()
    
    # 按日期排序
    national_data = national_data.sort_values('日期')
    
    # 去重
    national_data = national_data.drop_duplicates(subset=['日期'], keep='first')
    
    # 填充缺失日期
    if len(national_data) > 1:
        national_data['日期'] = pd.to_datetime(national_data['日期'])
        
        min_date = national_data['日期'].min()
        max_date = national_data['日期'].max()
        full_date_range = pd.date_range(start=min_date, end=max_date, freq='D')
        
        full_df = pd.DataFrame({'日期': full_date_range})
        national_data = full_df.merge(national_data, on='日期', how='left')
        
        # 线性插值填充缺失值
        national_data['猪肉价格'] = national_data['猪肉价格'].interpolate(method='linear')
        national_data['猪肉价格'] = national_data['猪肉价格'].ffill().bfill()
        
        # 填充其他列
        national_data['单位'] = national_data['单位'].fillna('元/公斤')
        national_data['地区'] = national_data['地区'].fillna('全国平均')
        
        national_data['日期'] = national_data['日期'].dt.strftime('%Y-%m-%d')
    
    return national_data.to_dict('records')

def main():
    print("=" * 70)
    print("猪肉价格数据获取程序")
    print("数据来源：农业农村部瘦肉型白条猪肉出厂价格监测周报")
    print("=" * 70)
    
    # 获取数据
    print("\n步骤1: 从农业农村部网站获取数据...")
    raw_data = fetch_and_process()
    
    if raw_data:
        print(f"\n总共获取到 {len(raw_data)} 条原始数据")
        
        # 生成完整时间序列
        print("\n步骤2: 生成完整的日度时间序列...")
        full_data = generate_full_timeseries(raw_data)
        
        if full_data:
            # 保存数据
            print("\n步骤3: 保存数据到CSV文件...")
            
            df = pd.DataFrame(full_data)
            df = df.sort_values('日期')
            
            output_file = 'pork_price_china_2023_2025.csv'
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            
            print(f"\n数据已保存到: {output_file}")
            print(f"最终数据量: {len(df)} 条")
            
            # 显示统计信息
            print(f"\n数据统计:")
            print(f"  - 日期范围: {df['日期'].min()} 至 {df['日期'].max()}")
            print(f"  - 价格范围: {df['猪肉价格'].min():.2f} - {df['猪肉价格'].max():.2f} 元/公斤")
            print(f"  - 平均价格: {df['猪肉价格'].mean():.2f} 元/公斤")
            
            # 显示数据预览
            print("\n数据预览 (前15条):")
            print(df.head(15).to_string(index=False))
            
            print("\n数据预览 (后15条):")
            print(df.tail(15).to_string(index=False))
            
        else:
            print("\n无法生成完整时间序列数据")
    else:
        print("\n无法获取原始数据")

if __name__ == "__main__":
    main()
