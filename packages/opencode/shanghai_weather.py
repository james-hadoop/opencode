#!/usr/bin/env python3
import requests
import csv
import json
from datetime import datetime, timedelta
import time
import sys

class ShanghaiWeatherData:
    def __init__(self):
        self.base_url = "https://archive-api.open-meteo.com/v1/archive"
        self.latitude = 31.2304  # Shanghai latitude
        self.longitude = 121.4737  # Shanghai longitude
        self.daily_data = []
    
    def get_weather_data(self, start_date, end_date):
        """获取指定日期范围内的天气数据"""
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "start_date": start_date,
            "end_date": end_date,
            "daily": "weathercode,temperature_2m_max,temperature_2m_min",
            "timezone": "Asia/Shanghai",
            "timezone_abbreviation": "0"
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.RequestException as e:
            print(f"请求失败: {e}")
            return None
    
    def weather_code_to_description(self, code):
        """将天气代码转换为中文描述"""
        weather_map = {
            0: "晴朗",
            1: "主要晴朗",
            2: "部分多云",
            3: "阴天",
            45: "雾",
            48: "雾凇",
            51: "小毛毛雨",
            53: "中毛毛雨",
            55: "浓毛毛雨",
            56: "冻毛毛雨",
            57: "浓冻毛毛雨",
            61: "小雨",
            63: "中雨",
            65: "大雨",
            66: "冻雨",
            67: "浓冻雨",
            71: "小雪",
            73: "中雪",
            75: "大雪",
            77: "雪粒",
            80: "小阵雨",
            81: "中阵雨",
            82: "大阵雨",
            85: "小阵雪",
            86: "大阵雪",
            95: "雷暴",
            96: "雷暴伴有小冰雹",
            99: "雷暴伴有大冰雹"
        }
        return weather_map.get(code, "未知")
    
    def process_data(self, data):
        """处理天气数据并添加到列表中"""
        if not data or 'daily' not in data:
            print("数据格式错误")
            return
        
        daily = data['daily']
        
        for i in range(len(daily['time'])):
            date = daily['time'][i]
            weather_code = daily['weathercode'][i]
            max_temp = daily['temperature_2m_max'][i]
            min_temp = daily['temperature_2m_min'][i]
            
            weather_desc = self.weather_code_to_description(weather_code)
            
            self.daily_data.append({
                'date': date,
                'weather': weather_desc,
                'max_temperature': max_temp,
                'min_temperature': min_temp
            })
    
    def save_to_csv(self, filename):
        """保存数据到CSV文件"""
        if not self.daily_data:
            print("没有数据可保存")
            return
        
        fieldnames = ['date', 'weather', 'max_temperature', 'min_temperature']
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.daily_data)
        
        print(f"数据已保存到 {filename}")
    
    def get_data_by_year(self, year):
        """按年获取数据"""
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        
        print(f"正在获取 {year} 年的天气数据...")
        data = self.get_weather_data(start_date, end_date)
        
        if data:
            self.process_data(data)
            print(f"{year} 年数据获取成功")
            return True
        else:
            print(f"{year} 年数据获取失败")
            return False

def main():
    weather = ShanghaiWeatherData()
    
    # 获取近3年的数据（2022-2025）
    years = [2022, 2023, 2024, 2025]
    
    for year in years:
        success = weather.get_data_by_year(year)
        if not success:
            print(f"警告：{year}年数据获取失败")
        time.sleep(1)  # 避免请求过于频繁
    
    if weather.daily_data:
        # 保存数据
        filename = "shanghai_weather_2022_2025.csv"
        weather.save_to_csv(filename)
        
        # 显示统计信息
        print(f"\n数据统计:")
        print(f"总记录数: {len(weather.daily_data)}")
        print(f"时间范围: {weather.daily_data[0]['date']} 至 {weather.daily_data[-1]['date']}")
        
        # 显示前几条数据作为示例
        print(f"\n前5条记录:")
        for i, record in enumerate(weather.daily_data[:5]):
            print(f"{i+1}. {record['date']}: {record['weather']}, 最高{record['max_temperature']}°C, 最低{record['min_temperature']}°C")
    else:
        print("未能获取任何数据")

if __name__ == "__main__":
    main()