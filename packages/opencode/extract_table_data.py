#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从农业农村部周报HTML中提取表格数据
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import re

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def extract_table_data(html_content, year):
    """从HTML中提取表格数据"""
    data = []
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 查找所有表格
    tables = soup.find_all('table', class_='MsoNormalTable')
    
    for table in tables:
        try:
            rows = table.find_all('tr')
            
            # 查找日期行（包含"月"和"日"的行）
            date_cells = []
            price_cells = []
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 6:
                    # 检查第一列是否是日期
                    first_cell_text = cells[0].get_text().strip()
                    date_match = re.search(r'(\d{1,2})[月\.\-](\d{1,2})[日\.\-]?', first_cell_text)
                    
                    if date_match:
                        month = int(date_match.group(1))
                        day = int(date_match.group(2))
                        
                        # 查找价格数据（通常在后面的列中）
                        for i in range(1, len(cells)):
                            cell_text = cells[i].get_text().strip()
                            price_match = re.search(r'(\d+\.?\d*)', cell_text)
                            
                            if price_match and i <= 5:  # 假设价格在前5列
                                price = float(price_match.group(1))
                                
                                try:
                                    date = datetime(year, month, day)
                                    
                                    data.append({
                                        '日期': date.strftime('%Y-%m-%d'),
                                        '猪肉价格': price,
                                        '单位': '元/公斤'
                                    })
                                    
                                    print(f"  提取到数据: {date.strftime('%Y-%m-%d')} - {price} 元/公斤")
                                    break
                                except:
                                    continue
                        
                        break  # 找到一个日期行后继续查找下一个表格
        
        except Exception as e:
            print(f"解析表格失败: {e}")
            continue
    
    return data

def fetch_page_data(url, year):
    """获取页面数据"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        
        if response.status_code == 200:
            return response.content
        else:
            print(f"  获取页面失败，HTTP状态码: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"  获取页面异常: {e}")
        return None

def main():
    print("=" * 60)
    print("从农业农村部网站提取猪肉价格数据")
    print("=" * 60)
    
    # 要访问的URL列表
    urls_to_fetch = [
        ("https://www.agri.cn/sj/jgzs/202511/t20251117_8786530.htm", 2025),  # 第46周
        ("https://www.agri.cn/sj/jgzs/202511/t20251111_8784970.htm", 2025),  # 第45周
        ("https://www.agri.cn/sj/jgzs/202510/t20251027_8780347.htm", 2025),  # 第42周
    ]
    
    all_data = []
    
    for url, year in urls_to_fetch:
        print(f"\n正在访问: {url}")
        
        html_content = fetch_page_data(url, year)
        
        if html_content:
            table_data = extract_table_data(html_content, year)
            if table_data:
                all_data.extend(table_data)
                print(f"  从该页面提取到 {len(table_data)} 条数据")
            else:
                print("  未能从该页面提取到数据")
        
        # 暂停一下，避免请求过快
        import time
        time.sleep(1)
    
    # 保存数据
    if all_data:
        print(f"\n总共获取到 {len(all_data)} 条数据")
        
        # 创建DataFrame
        df = pd.DataFrame(all_data)
        
        # 按日期排序
        df = df.sort_values('日期')
        
        # 去重
        df = df.drop_duplicates(subset=['日期'], keep='first')
        
        # 保存到CSV
        output_file = 'pork_price_data_real.csv'
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print(f"\n数据已保存到 {output_file}")
        print(f"最终数据量: {len(df)} 条")
        
        # 显示统计信息
        print(f"\n数据统计:")
        print(f"  - 日期范围: {df['日期'].min()} 至 {df['日期'].max()}")
        print(f"  - 价格范围: {df['猪肉价格'].min():.2f} - {df['猪肉价格'].max():.2f} 元/公斤")
        print(f"  - 平均价格: {df['猪肉价格'].mean():.2f} 元/公斤")
        
        # 显示数据预览
        print("\n数据预览:")
        print(df.head(10).to_string(index=False))
        
    else:
        print("\n未能获取到任何数据")

if __name__ == "__main__":
    main()
