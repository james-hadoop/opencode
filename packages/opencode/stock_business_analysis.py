#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票主营业务分析脚本
分析每只股票的主营业务并存储到 app.t_app_stock_business_inc_d 表
"""

import pymysql
import pandas as pd
from datetime import datetime


def get_db_connection():
    """创建数据库连接"""
    return pymysql.connect(
        host='localhost',
        port=3306,
        user='dev',
        password='dEv#1234',
        database='app',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )


def get_stock_list():
    """获取股票列表数据"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            SELECT ts_code, symbol, name, area, industry, cnspell, market, list_date, act_name, act_ent_type
            FROM app.t_app_stock_list_acc
            """
            cursor.execute(sql)
            return cursor.fetchall()
    finally:
        conn.close()


def analyze_business(stock):
    """分析股票主营业务"""
    industry = stock.get('industry', '') or ''
    act_name = stock.get('act_name', '') or ''
    name = stock.get('name', '') or ''
    
    business_list = []
    
    if act_name:
        business_list.append(act_name)
    elif industry:
        business_list.append(industry)
    
    if not business_list:
        business_list.append(f"股票{stock.get('symbol', '')}")
    
    return '|'.join(business_list[:3]) if len(business_list) > 1 else business_list[0] if business_list else ''


def check_table_exists():
    """检查目标表是否存在，不存在则创建"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS app.t_app_stock_business_inc_d (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                ts_code VARCHAR(20) NOT NULL COMMENT 'TS代码',
                symbol VARCHAR(20) COMMENT '股票代码',
                name VARCHAR(100) COMMENT '股票名称',
                area VARCHAR(50) COMMENT '所在地区',
                industry VARCHAR(100) COMMENT '所属行业',
                business VARCHAR(500) COMMENT '主营业务',
                list_date VARCHAR(20) COMMENT '上市日期',
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_ts_code (ts_code),
                INDEX idx_symbol (symbol)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票主营业务表'
            """)
            conn.commit()
            print("✓ 表 t_app_stock_business_inc_d 已检查/创建")
    finally:
        conn.close()


def save_business_data(stocks):
    """保存主营业务数据到数据库"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            for stock in stocks:
                business = analyze_business(stock)
                ts_code = stock.get('ts_code', '')
                
                cursor.execute("""
                INSERT INTO app.t_app_stock_business_inc_d 
                (ts_code, symbol, name, area, industry, business, list_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    symbol = VALUES(symbol),
                    name = VALUES(name),
                    area = VALUES(area),
                    industry = VALUES(industry),
                    business = VALUES(business),
                    list_date = VALUES(list_date)
                """, (
                    ts_code,
                    stock.get('symbol', ''),
                    stock.get('name', ''),
                    stock.get('area', ''),
                    stock.get('industry', ''),
                    business,
                    stock.get('list_date', '')
                ))
            
            conn.commit()
            print(f"✓ 已保存 {len(stocks)} 条主营业务数据")
    finally:
        conn.close()


def main():
    print("=" * 70)
    print("股票主营业务分析程序")
    print("=" * 70)
    
    # 检查/创建表
    check_table_exists()
    
    # 获取股票列表
    print("\n正在获取股票列表数据...")
    stocks = get_stock_list()
    print(f"✓ 获取到 {len(stocks)} 只股票")
    
    # 分析并保存
    print("\n正在分析主营业务并保存...")
    save_business_data(stocks)
    
    print("\n✓ 程序执行完成！")


if __name__ == "__main__":
    main()
