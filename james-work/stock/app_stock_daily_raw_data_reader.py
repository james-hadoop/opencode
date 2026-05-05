import argparse
import sys
import os
import time
import akshare as ak

from python_app.config import Config
from python_app.lib.date_util import DateUtil
from python_app.processor import Processor
from python_app.lib.data_query_util import DataQueryUtil
from python_app.lib.data_write_util import DataWriteUtil
from python_app.lib.stock_util import StockUtil

def process(config:Config, dt:str):
    """
    # common_config
    start_dt, end_dt = config.start_dt, config.end_dt
    start_dt_int, end_dt_int = DateUtil.dt_to_int(start_dt), DateUtil.dt_to_int(end_dt)
    dt_list = DateUtil.get_dt_list(start_dt, end_dt)
    dt_range = config.dt_range
    dt_int_range = config.dt_int_range

    # file_config
    input_path, output_path = config.input_path, config.output_path

    # db_config
    db_connection_string = config.get_db_connection_string()
    db_sql = config.get_db_sql()

    # ai_config
    prompt_template = config.prompt_template
    """
    start_dt, end_dt = config.start_dt, config.end_dt
    start_dt_int, end_dt_int = DateUtil.dt_to_int(start_dt), DateUtil.dt_to_int(end_dt)

    db_config = config.get_db_config()
    database = db_config['database']
    table = db_config['table']
    sql = config.get_db_sql()
    
    print(f"start_dt = {start_dt}, end_dt = {end_dt}")
    print(f"db_table = {database}.{table}")
    print(f"sql =\n\n {sql}\n")

    stock_df = DataQueryUtil.read_from_db(config.get_db_sql(), config.get_db_connection_string())
    print(f"Got {len(stock_df)} stocks to process")
    print(stock_df.head(5))
    
    success_count = 0
    fail_count = 0
    
    # # 只处理前3只股票用于测试
    # test_count = 3
    # stock_df = stock_df.head(test_count)
    # print(f"\n[TEST MODE] Only processing first {test_count} stocks\n")
    
    for ts_code_with_suffix in stock_df['ts_code_with_suffix']:
        print(f"Processing ts_code_with_suffix: {ts_code_with_suffix} @ {DateUtil.get_now_datetime()}")

        ts_code, ts_code_suffix = ts_code_with_suffix.split('.', 1)[0], ts_code_with_suffix.split('.', 1)[1]
        ts_code_suffix = f".{ts_code_suffix}"

        # 使用新的 get_stock_data 方法，自动根据后缀选择正确的接口
        df = StockUtil.get_stock_data(ts_code, start_dt, end_dt, ts_code_suffix=ts_code_suffix)
        
        if df is None or df.empty:
            print(f"警告: 未能获取股票 {ts_code} 的数据，跳过写入")
            fail_count += 1
            print("-" * 128)
            time.sleep(5)
            continue
        
        formatted_df = StockUtil.format_stock_df(df, ts_code_suffix).copy()
        print(formatted_df.head(5))
        
        DataWriteUtil.write_to_db_with_create_info_dt(formatted_df, table, config.get_db_connection_string(), dt)
        
        print(f"成功处理 ts_code: {ts_code} ")
        print("-" * 128)
        success_count += 1
        time.sleep(10)
    
    print(f"\n处理完成: 成功 {success_count} 条, 失败 {fail_count} 条")

def main():
    parser = argparse.ArgumentParser(description="Process data with dynamic dt and config_path.")
    parser.add_argument("-d", "--dt", type=str, default="2025-10-01", help="Date parameter (default: '2025-10-01')")
    parser.add_argument("-c", "--config_path", type=str, default="D:/_AllDocMap/02_Project/gitee/python-app/python_app/config/app_stock_szse_data_reader.yaml", help="Path to the config file (default: 'your_config.yaml')")
    parser.add_argument("-n", "--max_runs", type=int, default=1, help="Maximum number of runs (default: 1)")
    args = parser.parse_args()

    config_path = "/Users/Shared/_AllDocMap/02_Project/gitee/python-app/app_local/stock/config/app_stock_daily_raw_data_reader.yaml"
    config = Config(config_path)
    dt = "2026-02-01"
    
    max_runs = args.max_runs

    processor=Processor(process=lambda: process(config, dt))
    processor.do_process()

if __name__ == '__main__':
    max_runs = 1  # 默认只运行1次，避免超时
    for i in range(1, max_runs + 1):
        print("-" * 128)
        print(f"第{i}次运行")
        print("-" * 128)
        main()