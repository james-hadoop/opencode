#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取全国猪肉价格数据
数据来源：农业农村部瘦肉型白条猪肉出厂价格指数
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import time
import re
import os

# 禁用SSL警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class PorkPriceFetcher:
    def __init__(self):
        self.base_url = "https://www.agri.cn/sj/jgzs/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
    
    def get_weekly_reports(self, start_year=2023, end_year=2025):
        """获取瘦肉型白条猪肉出厂价格监测周报数据"""
        all_data = []
        
        for year in range(start_year, end_year + 1):
            for week_num in range(1, 53):
                try:
                    urls = [
                        f"https://www.agri.cn/sj/jgzs/{year}/t{year}{week_num:02d}/index.htm",
                        f"https://www.agri.cn/sj/jgzs/{year}/t{year}0{week_num if week_num < 10 else week_num}01_0000000.htm",
                    ]
                    
                    for url in urls:
                        try:
                            response = self.session.get(url, timeout=10, verify=False)
                            if response.status_code == 200:
                                soup = BeautifulSoup(response.content, 'html.parser')
                                data = self.parse_weekly_report(soup, year, week_num)
                                if data:
                                    all_data.extend(data)
                                    print(f"成功获取 {year}年第{week_num}周数据")
                                    break
                        except Exception as ex:
                            continue
                    
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"获取 {year}年第{week_num}周数据失败: {e}")
                    continue
        
        return all_data
    
    def parse_weekly_report(self, soup, year, week_num):
        """解析周报数据"""
        data = []
        
        try:
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 5:
                        text = ' '.join([cell.get_text().strip() for cell in cells])
                        
                        # 查找日期模式
                        date_match = re.search(r'(\d{1,2})月(\d{1,2})日', text)
                        if date_match:
                            month = int(date_match.group(1))
                            day = int(date_match.group(2))
                            
                            # 查找价格
                            price_match = re.search(r'(\d+\.?\d*)\s*元/公斤', text)
                            if price_match:
                                price = float(price_match.group(1))
                                
                                try:
                                    date = datetime(year, month, day)
                                    
                                    data.append({
                                        '日期': date.strftime('%Y-%m-%d'),
                                        '价格': price,
                                        '单位': '元/公斤',
                                        '年份': year,
                                        '周数': week_num
                                    })
                                except:
                                    continue
        
        except Exception as e:
            print(f"解析周报数据失败: {e}")
        
        return data
    
    def get_daily_price_index(self):
        """获取瘦肉型白条猪肉出厂价格总指数的日度数据"""
        url = "https://capes.agri.cn/weixin/pigPrice"
        
        try:
            response = self.session.get(url, timeout=10, verify=False)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                index_elements = soup.find_all(class_=['index-value', 'price-index'])
                
                data = []
                for elem in index_elements:
                    text = elem.get_text().strip()
                    if text.replace('.', '').isdigit():
                        data.append({
                            '日期': datetime.now().strftime('%Y-%m-%d'),
                            '指数': float(text),
                            '类型': '瘦肉型白条猪肉出厂价格总指数'
                        })
                
                return data
                
        except Exception as e:
            print(f"获取日度指数数据失败: {e}")
        
        return []
    
    def save_to_csv(self, data, filename='pork_price_data.csv'):
        """保存数据到CSV文件"""
        if not data:
            print("没有数据可保存")
            return
        
        try:
            df = pd.DataFrame(data)
            
            df = df.sort_values('日期')
            df = df.drop_duplicates(subset=['日期'], keep='first')
            
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"数据已保存到 {filename}")
            print(f"共获取 {len(df)} 条数据")
            
            return df
            
        except Exception as e:
            print(f"保存数据失败: {e}")
            return None

def main():
    print("开始获取猪肉价格数据...")
    
    fetcher = PorkPriceFetcher()
    
    print("正在获取瘦肉型白条猪肉出厂价格监测周报数据...")
    weekly_data = fetcher.get_weekly_reports(2023, 2025)
    
    if weekly_data:
        print(f"获取到 {len(weekly_data)} 条周报数据")
    
    print("正在获取日度价格指数数据...")
    daily_index = fetcher.get_daily_price_index()
    
    if daily_index:
        print(f"获取到 {len(daily_index)} 条日度指数数据")
    
    all_data = weekly_data + daily_index
    
    if all_data:
        df = fetcher.save_to_csv(all_data)
        
        if df is not None:
            print("\n数据预览:")
            print(df.head(10))
    else:
        print("未能获取到任何数据")

if __name__ == "__main__":
    main()
