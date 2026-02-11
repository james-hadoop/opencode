#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从农业农村部周报中提取真实的猪肉价格数据
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import time
import re
import json

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class RealPorkDataFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
        
        # 农业农村部瘦肉型白条猪肉出厂价格监测周报URL列表
        self.urls = {
            2025: [
                "https://www.agri.cn/sj/jgzs/202511/t20251117_8786530.htm",  # 第46周
                "https://www.agri.cn/sj/jgzs/202511/t20251111_8784970.htm",  # 第45周
                "https://www.agri.cn/sj/jgzs/202510/t20251027_8780347.htm",  # 第42周
            ],
            2024: [
                "https://www.agri.cn/sj/jgzs/202501/t20250102_8703329.htm",  # 第52周
                "https://www.agri.cn/sj/jgzs/202412/t20241225_8701486.htm",  # 第51周
            ]
        }
    
    def parse_table_data(self, table, year):
        """解析表格数据"""
        data = []
        
        try:
            rows = table.find_all('tr')
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 5:
                    text = ' '.join([cell.get_text().strip() for cell in cells])
                    
                    # 查找日期行（如：10月13日）
                    date_match = re.search(r'(\d{1,2})[月\.\-](\d{1,2})[日\.\-]?', text)
                    
                    if date_match:
                        month = int(date_match.group(1))
                        day = int(date_match.group(2))
                        
                        # 查找价格数据
                        prices = re.findall(r'(\d+\.?\d*)\s*元', text)
                        
                        if prices and len(prices) >= 1:
                            try:
                                date = datetime(year, month, day)
                                price = float(prices[0])
                                
                                data.append({
                                    '日期': date.strftime('%Y-%m-%d'),
                                    '猪肉价格': price,
                                    '单位': '元/公斤',
                                    '来源': '农业农村部瘦肉型白条猪肉出厂价格监测周报'
                                })
                            except:
                                continue
        
        except Exception as e:
            print(f"解析表格数据失败: {e}")
        
        return data
    
    def fetch_weekly_reports(self):
        """获取周报数据"""
        all_data = []
        
        for year, urls in self.urls.items():
            print(f"\n正在获取 {year} 年的数据...")
            
            for url in urls:
                try:
                    print(f"  正在访问: {url}")
                    
                    response = self.session.get(url, timeout=15, verify=False)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # 查找所有表格
                        tables = soup.find_all('table')
                        
                        for table in tables:
                            table_data = self.parse_table_data(table, year)
                            if table_data:
                                all_data.extend(table_data)
                                print(f"    从该页面获取到 {len(table_data)} 条数据")
                    
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"  访问失败: {e}")
                    continue
        
        return all_data
    
    def fill_missing_dates(self, data):
        """填充缺失的日期数据（使用线性插值）"""
        if not data:
            return data
        
        # 创建DataFrame
        df = pd.DataFrame(data)
        
        # 确保日期列是datetime类型
        df['日期'] = pd.to_datetime(df['日期'])
        
        # 按日期排序
        df = df.sort_values('日期')
        
        # 创建完整的日期范围
        min_date = df['日期'].min()
        max_date = df['日期'].max()
        full_date_range = pd.date_range(start=min_date, end=max_date, freq='D')
        
        # 创建完整的DataFrame
        full_df = pd.DataFrame({'日期': full_date_range})
        
        # 合并数据
        df = full_df.merge(df, on='日期', how='left')
        
        # 填充缺失值（使用前向填充和后向填充）
        df['猪肉价格'] = df['猪肉价格'].interpolate(method='linear')
        df['猪肉价格'] = df['猪肉价格'].ffill().bfill()
        
        # 填充其他列
        df['单位'] = df['单位'].fillna('元/公斤')
        df['来源'] = df['来源'].fillna('数据插值')
        
        # 格式化日期
        df['日期'] = df['日期'].dt.strftime('%Y-%m-%d')
        
        return df.to_dict('records')
    
    def save_to_csv(self, data, filename='pork_price_real_data.csv'):
        """保存数据到CSV文件"""
        if not data:
            print("没有数据可保存")
            return None
        
        try:
            df = pd.DataFrame(data)
            
            # 按日期排序
            df = df.sort_values('日期')
            
            # 去重
            df = df.drop_duplicates(subset=['日期'], keep='first')
            
            # 保存到CSV
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"\n数据已保存到 {filename}")
            print(f"共获取 {len(df)} 条数据")
            
            return df
            
        except Exception as e:
            print(f"保存数据失败: {e}")
            return None

def main():
    print("=" * 60)
    print("真实的猪肉价格数据获取程序")
    print("数据来源：农业农村部瘦肉型白条猪肉出厂价格监测周报")
    print("=" * 60)
    
    fetcher = RealPorkDataFetcher()
    
    # 获取真实数据
    print("\n步骤1: 从农业农村部网站获取真实数据...")
    real_data = fetcher.fetch_weekly_reports()
    
    if real_data:
        print(f"\n成功获取 {len(real_data)} 条真实数据")
        
        # 尝试填充缺失的日期
        print("\n步骤2: 填充缺失的日期数据...")
        filled_data = fetcher.fill_missing_dates(real_data)
        
        if filled_data:
            # 保存数据
            df = fetcher.save_to_csv(filled_data)
            
            if df is not None:
                # 显示统计信息
                print("\n数据统计:")
                print(f"  - 日期范围: {df['日期'].min()} 至 {df['日期'].max()}")
                print(f"  - 猪肉价格范围: {df['猪肉价格'].min():.2f} - {df['猪肉价格'].max():.2f} 元/公斤")
                print(f"  - 平均价格: {df['猪肉价格'].mean():.2f} 元/公斤")
                
                # 显示部分数据
                print("\n数据预览 (前10条):")
                print(df.head(10).to_string(index=False))
    else:
        print("\n无法从官方网站获取数据，请检查网络连接或稍后重试")

if __name__ == "__main__":
    main()
