### 目录

- [目录](#目录)
- [下载B站视频](#下载b站视频)
  - [下载单个B站视频](#下载单个b站视频)
  - [下载B站视频列表](#下载b站视频列表)
- [下载 youtube 视频](#下载-youtube-视频)
  - [下载单个 youtube 视频](#下载单个-youtube-视频)
- [精简文件名](#精简文件名)
  - [精简指定目录下的文件名](#精简指定目录下的文件名)
  - [根据文件名称，找到缺失的文件](#根据文件名称找到缺失的文件)
- [markdown 文件操作](#markdown-文件操作)
  - [为 markdown 文件的指定标题添加目录导航](#为-markdown-文件的指定标题添加目录导航)
  - [markdown 目录自动更新](#markdown-目录自动更新)

---

### 下载B站视频 [<sub>返回目录</sub>](#目录)

#### 下载单个B站视频 [<sub>返回目录</sub>](#目录)

**prompt**

```md
将这个视频文件下载到 /Volumes/james1t/\_AllDocMap/03_Learn/全国软考系统架构设计师/ 目录下，下载完毕后，打印出完整的视频路径

https://www.bilibili.com/video/BV1sKiyB9Eac?spm_id_from=333.788.videopod.episodes&vd_source=46c88a014c6f2fefbdb68e4d09b7739b

注意：

1. 如果涉及到使用 python 运行环境，使用 /Users/Shared/\_AllDocMap/02_Project/gitee/james-python/.conda/bin/python 这个 python 环境

2. 视频文件对应的音频要一并下载，并合并成一个视频文件
```

**action**

```python

/Users/Shared/_AllDocMap/02_Project/gitee/james-python/.conda/bin/python -m yt_dlp -f "30080+30280" --merge-output-format mp4 "https://www.bilibili.com/video/BV1ThS1BYESp?p=21" -o "~/Downloads/%(playlist_index)s-%(title)s.%(ext)s" --no-playlist --force-overwrites

```

#### 下载B站视频列表 [<sub>返回目录</sub>](#目录)

**prompt**

```

自动完成第1集到第198集的视频下载

```

**thinking**

```thinking

Thinking: 用户想要下载从第1集到第198集的所有视频。我需要使用 yt-dlp 来下载整个播放列表。
参数应该包括：
1. 指定使用指定的 Python 环境
2. 使用 -f "30080+30280" 来获取视频和音频并合并
3. 使用 --merge-output-format mp4
4. 使用 -o "~/Downloads/%(playlist_index)s-%(title)s.%(ext)s" 来格式化输出文件名
5. 不要使用 --no-playlist，这样会下载整个播放列表
由于是198集视频，这可能需要很长时间。我应该直接开始下载。

```

**action**

```

/Users/Shared/_AllDocMap/02_Project/gitee/james-python/.conda/bin/python -m yt_dlp -f "30080+30280" --merge-output-format mp4 "https://www.bilibili.com/video/BV1sKiyB9Eac?spm_id_from=333.788.videopod.episodes&vd_source=46c88a014c6f2fefbdb68e4d09b7739b" -o "/Volumes/james1t/_AllDocMap/03_Learn/全国软考系统架构设计师/%(playlist_index)s-%(title)s.%(ext)s"

```

### 下载 youtube 视频 [<sub>返回目录</sub>](#目录)

#### 下载单个 youtube 视频 [<sub>返回目录</sub>](#目录)

**prompt**

```

将这个页面中视频文件列表下载到 /Volumes/james1t/_AllDocMap/22_Entertainment/growing_pains/ 目录下，下载完毕后，打印出完整的视频路径

https://www.bilibili.com/video/BV1RhyaB4E2x?spm_id_from=333.788.recommend_more_video.1&trackid=web_related_0.router-related-2206419-76tx6.1769208583494.42&vd_source=46c88a014c6f2fefbdb68e4d09b7739b

注意：

1. 如果涉及到使用 python 运行环境，使用 /Users/Shared/_AllDocMap/02_Project/gitee/james-python/.conda/bin/python 这个 python 环境

2. 每一个视频文件对应的音频要一并下载，并合并成一个视频文件

```

### 精简文件名 [<sub>返回目录</sub>](#目录)

#### 精简指定目录下的文件名 [<sub>返回目录</sub>](#目录)

**prompt**

```

将以下指定目录下的文件的文件名精简，精简之后的文件名保留第几集以及文件内容摘要信息

/Volumes/james1t/_AllDocMap/03_Learn/全国软考系统架构设计师/

```

**action**

```

cd "/Volumes/james1t/_AllDocMap/03_Learn/全国软考系统架构设计师/" && python3 -c "
import os
import re
for filename in os.listdir('.'):
    if filename.endswith('.mp4'):
        # Extract episode number using regex
        episode_match = re.search(r'p(\d+)\s+', filename)
        if episode_match:
            episode = episode_match.group(1)

            # Extract content after 'pXX '
            content = re.sub(r'.*p\d+\s+', '', filename)
            content = content.replace('.mp4', '')

            # Create new filename
            new_name = f'第{episode}集-{content}.mp4'

            print(f'mv \"{filename}\" \"{new_name}\"')
" | head -10

```

```

cd "/Volumes/james1t/_AllDocMap/03_Learn/全国软考系统架构设计师/" && python3 -c "
import os
import re
renamed_count = 0
for filename in os.listdir('.'):
    if filename.endswith('.mp4'):
        # Extract episode number using regex
        episode_match = re.search(r'p(\d+)\s+', filename)
        if episode_match:
            episode = episode_match.group(1)

            # Extract content after 'pXX '
            content = re.sub(r'.*p\d+\s+', '', filename)
            content = content.replace('.mp4', '')

            # Create new filename
            new_name = f'第{episode}集-{content}.mp4'

            # Execute rename
            os.rename(filename, new_name)
            renamed_count += 1
            print(f'Renamed: {filename} -> {new_name}')
print(f'Total files renamed: {renamed_count}')
"

```

#### 根据文件名称，找到缺失的文件 [<sub>返回目录</sub>](#目录)

**prompt**

```

这个目录下的集数是连续的吗？如果不连续，缺失的是第几集？

```

**action**

```

cd "/Volumes/james1t/_AllDocMap/03_Learn/全国软考系统架构设计师/" && python3 -c "
import os
import re
# Extract episode numbers
episodes = []
for filename in os.listdir('.'):
    if filename.endswith('.mp4'):
        match = re.search(r'第(\d+)集', filename)
        if match:
            episodes.append(int(match.group(1)))
episodes.sort()
print('现有集数:', len(episodes))
print('集数列表:', episodes)
# Find missing episodes
all_episodes = set(range(min(episodes), max(episodes) + 1))
missing = sorted(all_episodes - set(episodes))
if missing:
    print('缺失的集数:', missing)
    print('共缺失:', len(missing), '集')
else:
    print('集数连续，无缺失')
"

```

#### 重命名图片文件 [<sub>返回目录</sub>](#目录)

**prompt**

```

将以下指定目录下的图片文件名包含中文字符的图片文件，根据中文含义重命名成只包含英文字符的文件名，文件名的规则保持：主题--公司名称-图片内容摘要 这一规则 。

注意：避免重命名成相同名称的图片文件之后，出现图片覆盖的情况而导致图片丢失。要保证重命名后的图片文件名称是唯一的。

/Users/james/Downloads/images/

```

```

将以下指定目录下的图片文件名称进行重命名。重命名之后的文件名称的格式为：主题--公司名称-图片内容摘要.图片格式，如：governance--kuaishou-data_asset.jpeg、business--nobody-management_system_2.jpeg、lakehouse--nobody-warehouse_layer.jpeg 等。其中，当无法判断是哪一家公司时，公司名称用 nobody 代替。

主题的名称的枚举值包含在 /Users/Shared/_AllDocMap/02_Project/gitee/james-KNote/README.md 文件的中的主题分类。

注意：避免重命名成相同名称的图片文件之后，出现图片覆盖的情况而导致图片丢失。要保证重命名后的图片文件名称是唯一的。

/Users/james/Downloads/images/

```

```

找到以下指定目录中所有的图片文件，文件名的命名格式遵循：主题--公司名称-图片内容摘要 这个规则。将目录中的图片内容摘要信息无法提现出内容含义的图片进行重命名，图片内容摘要的描述不超过30个字符

/Users/james/Downloads/images/

```

**action**

```

cd "/Users/james/Downloads/images" && find . -name "*--*" -type f | grep -E "^[^-]+--[a-zA-Z0-9_-]+" | grep -E "(image|photo|screenshot|07_|08_|09_|12_|1_|screen|pic|img|jpg_|jpeg_|png_)" | wc -l

```

```

- analysis--nobody-analysis_architecture.png → 数据分析架构图
- portrait--jd-user_profiling_system.png → 用户画像系统
- governance--kuaishou-data_governance_platform.jpeg → 数据治理平台
- metrics--meituan-data_metrics.png → 数据指标
- business--sensors-business_intelligence.png → 商业智能
- lakehouse--nobody-lakehouse_architecture.jpg → 湖仓架构
- olap--vipshop-clickhouse_optimization.jpg → Clickhouse优化
- platform--xiaomi-realtime_data_platform.jpg → 实时数据平台
- scheduler--alibaba-job_scheduling.png → 作业调度
- ai--nobody-ai_integration.png → AI集成

```


### markdown 文件操作 [<sub>返回目录</sub>](#目录)

#### 为 markdown 文件的指定标题添加目录导航 [<sub>返回目录</sub>](#目录)

**prompt**

```

为以下指定 markdown 文件的三级标题和四级标题增加字符串""" [<sub>返回目录</sub>](#目录) """，用快速返回到该页面顶部的目录导航，如果标题所在行已经包含了该字符串，则忽略添加。

/Users/Shared/_AllDocMap/02_Project/github/opencode/james-work/opencode-skill.md

```

#### markdown 目录自动更新 [<sub>返回目录</sub>](#目录)

**prompt**

```

增强以下指定 markdown 文件的目录导航功能，支持：文件内容更新之后，目录自动更新。

注意：新生成的导航目录结构、格式与原文件的目录结构、格式保持一致。

/Users/Shared/_AllDocMap/02_Project/github/opencode/james-work/opencode-skill.md

```

**action**

```python

import re
import os

def update_markdown_toc(file_path):
    """
    自动更新markdown文件的目录
    """
    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找所有三级和四级标题
    lines = content.split('\n')
    toc_lines = []
    h3_titles = []

    for line in lines:
        # 匹配三级标题 (### 标题)
        h3_match = re.match(r'^###\s+(.+?)(?:\s*\[<sub>返回目录</sub>\]\(#目录\))?$', line)
        if h3_match:
            title = h3_match.group(1).strip()
            anchor = generate_anchor(title)
            h3_titles.append((title, anchor))
            toc_lines.append(f"- [{title}](#{anchor})")

        # 匹配四级标题 (#### 标题)
        h4_match = re.match(r'^####\s+(.+?)(?:\s*\[<sub>返回目录</sub>\]\(#目录\))?$', line)
        if h4_match and h3_titles:
            title = h4_match.group(1).strip()
            anchor = generate_anchor(title)
            toc_lines.append(f"  - [{title}](#{anchor})")

    # 生成新的目录内容
    new_toc = "### 目录\n\n" + "\n".join(toc_lines) + "\n"

    # 查找原有目录的位置并替换
    toc_pattern = r'^### 目录\n.*?(?=\n---|\n### [^#])'
    match = re.search(toc_pattern, content, re.MULTILINE | re.DOTALL)

    if match:
        # 替换原有目录
        updated_content = re.sub(toc_pattern, new_toc.strip(), content, flags=re.MULTILINE | re.DOTALL)
    else:
        # 如果没有找到原有目录，在文件开头插入
        updated_content = new_toc + "\n---\n\n" + content

    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)

    print(f"目录已更新: {file_path}")
    print(f"找到 {len(h3_titles)} 个三级标题")

def generate_anchor(title):
    """
    生成markdown锚点链接
    """
    # 移除特殊字符，保留中文、英文、数字
    anchor = re.sub(r'[^\w\u4e00-\u9fff\s-]', '', title)
    # 替换空格为短横线
    anchor = re.sub(r'\s+', '-', anchor.strip())
    # 转换为小写
    return anchor.lower()

# 使用示例
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = "/Users/Shared/_AllDocMap/02_Project/github/opencode/james-work/opencode-skill.md"

    update_markdown_toc(file_path)

# 使用方法：
# python3 update_toc.py [markdown文件路径]
# 如果不指定文件路径，默认处理 opencode-skill.md

```


### 制作 PPT

#### 使用 kimi-k2.5-free 制作 PPT [<sub>返回目录</sub>](#目录)

**prompt**

```

你是一名资深大数据架构师，精通大数据技术、指标体系和大模型应用，将 /Users/james/Downloads/ws4opencode/_LGTM_数据指标_大应--NoETL自动化指标平台打造分析自由_Aloudata大应科技 的内容整理成20页以内的 PPT

如果涉及到使用 python 运行环境，使用 /Users/Shared/\_AllDocMap/02_Project/gitee/james-python/.conda/bin/python 这个 python 环境

PPT 的格式是 pptx，制作完成后，将PPT 保存到 /Users/james/Downloads/ws4opencode/ppt 目录下

```

**action**

```

ls -la "/Users/james/Downloads/ws4opencode/"

```

```

find "/Users/james/Downloads/ws4opencode/_LGTM_数据指标_大应--NoETL自动化指标平台打造分析自由_Aloudata大应科技" -type f 2>/dev/null | head -20

```

```

cd /Users/james/Downloads/ws4opencode/ppt && /Users/Shared/_AllDocMap/02_Project/gitee/james-python/.conda/bin/python generate_ppt.py

```


### 猪肉价格


#### dd

**prompt**

```

查询全国近3年每天的猪肉价格和猪肉成交量，存储成 csv 文件。其中，日期的格式为 yyyy-MM-dd 字符串

注意：

1. 如果涉及到使用 python 运行环境，使用 /Users/Shared/\_AllDocMap/02_Project/gitee/james-python/.conda/bin/python 这个 python 环境

```

### 股票分析

#### 分析股票买卖建议

**prompt**

```

根据历史股票价格数据，分析出买卖建议，并存储到 mysql 数据表 app.t_app_stock_trade_suggest_inc_d 中

注意：

分析的建议包括：
1. 分别分析 day_of_week ,day_of_month 这两个维度的买入时机
2. 买入时机与前3天成交量的相关性


如果涉及到使用 python 运行环境，使用 /Users/Shared/\_AllDocMap/02_Project/gitee/james-python/.conda/bin/python 这个 python 环境

数据库连接信息：
  mysql:
    charset: utf8mb4
    driver: mysql+pymysql  
    host: localhost
    port: 3306
    user: dev
    password: "dEv#1234"
    database: app
    table: t_app_stock_business_inc_d

mysql 查询语句：


SELECT  ts_name
       ,data_date
       ,data_month
       ,data_year
       ,ts_code
       ,ts_code AS formatted_ts_code
       ,shou_pan
       ,zhang_die_fu
       ,cheng_jiao_liang
       ,huan_shou_lv
       ,day_of_week
       ,day_of_month
FROM dwd.dwd_stock_daily_data_with_name_and_date_attr_acc_d
WHERE dt = '2026-01-31'
AND ts_name = '农业银行'
;

```

```

分别计算2025年成交量和收盘价的10分位数、20分位数、30分位数、40分位数、50分位数、60分位数、70分位数、80分位数、90分位数、100分位数

```

**action**

```python

import pymysql
import pandas as pd
import numpy as np
from scipy import stats
conn = pymysql.connect(
    host='localhost',
    port=3306,
    user='dev',
    password='dEv#1234',
    charset='utf8mb4'
)
df = pd.read_sql("""
SELECT data_date, cheng_jiao_liang, shou_pan
FROM dwd.dwd_stock_daily_data_with_name_and_date_attr_acc_d
WHERE ts_name = '农业银行'
AND data_date >= '2025-01-01'
AND data_date <= '2025-12-31'
ORDER BY data_date
""", conn)
df['volume'] = df['cheng_jiao_liang']
df['price'] = df['shou_pan']
print("=" * 60)
print("农业银行 2025年 时间序列相关性分析")
print("=" * 60)
# 1. Pearson相关系数
pearson_corr, pearson_p = stats.pearsonr(df['volume'], df['price'])
print(f"\n1. Pearson相关系数 (衡量线性相关性)")
print(f"   相关系数: {pearson_corr:.4f}")
print(f"   P值: {pearson_p:.4e}")
# 2. Spearman相关系数 (衡量单调相关性)
spearman_corr, spearman_p = stats.spearmanr(df['volume'], df['price'])
print(f"\n2. Spearman秩相关系数 (衡量单调相关性)")
print(f"   相关系数: {spearman_corr:.4f}")
print(f"   P值: {spearman_p:.4e}")
# 3. 成交量变化率与价格变化率的相关性
df['volume_pct'] = df['volume'].pct_change()
df['price_pct'] = df['price'].pct_change()
df_clean = df.dropna()
pearson_change, _ = stats.pearsonr(df_clean['volume_pct'], df_clean['price_pct'])
spearman_change, _ = stats.spearmanr(df_clean['volume_pct'], df_clean['price_pct'])
print(f"\n3. 变化率相关性 (日环比)")
print(f"   Pearson: {pearson_change:.4f}")
print(f"   Spearman: {spearman_change:.4f}")
# 4. 价格滞后相关性 (成交量领先/滞后)
print(f"\n4. 价格滞后相关性分析")
lags = range(-5, 6)
lag_corrs = []
for lag in lags:
    if lag < 0:
        corr = df['volume'].iloc[:lag].corr(df['price'].iloc[-lag:])
    elif lag > 0:
        corr = df['volume'].iloc[lag:].corr(df['price'].iloc[:-lag])
    else:
        corr = df['volume'].corr(df['price'])
    lag_corrs.append(corr)
    print(f"   滞后{lag:+d}天: {corr:.4f}")
# 5. 滚动相关性
print(f"\n5. 滚动相关性 (20日窗口)")
df['rolling_corr'] = df['volume'].rolling(window=20).corr(df['price'])
print(f"   平均滚动相关性: {df['rolling_corr'].mean():.4f}")
print(f"   滚动相关性范围: [{df['rolling_corr'].min():.4f}, {df['rolling_corr'].max():.4f}]")
# 6. 格兰杰因果检验 (简化版)
print(f"\n6. 简要分析结论")
if abs(pearson_corr) < 0.3:
    strength = "弱"
elif abs(pearson_corr) < 0.6:
    strength = "中等"
else:
    strength = "强"
    
direction = "正相关" if pearson_corr > 0 else "负相关"
print(f"   相关性强度: {strength}")
print(f"   相关方向: {direction}")
print("\n" + "=" * 60)
conn.close()

```

#### 分析股票的主营业务

**prompt**

```

根据以下数据库连接信息和股票查询语句，分析出每个股票的主营业务，并存储到 mysql 数据表 app.t_app_stock_business_inc_d 中

注意：

1. 如果涉及到使用 python 运行环境，使用 /Users/Shared/\_AllDocMap/02_Project/gitee/james-python/.conda/bin/python 这个 python 环境

数据库连接信息：
  mysql:
    charset: utf8mb4
    driver: mysql+pymysql  
    host: localhost
    port: 3306
    user: dev
    password: "dEv#1234"
    database: app
    table: t_app_stock_business_inc_d

mysql 查询语句：

SELECT ts_code, symbol, name, area, industry, cnspell, market, list_date, act_name, act_ent_type
FROM app.t_app_stock_list_acc;



```

### 数据库操作

#### 根据已有的数据表，新建数据表

**prompt**

```

根据 本机 mysql 数据库中  app.t_app_pdf_meta_acc definition 的 建表语句，创建数据表：app.t_app_toutiao_article_acc，其中 [Pasted ~4 lines]  是必选字`created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` char(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '' COMMENT '创建人员',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `updated_by` char(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '' COMMENT '更新人员',配置文件：/Users/Shared/_AllDocMap/02_Project/gitee/python-app/app_local/article/config/app_article_config.yaml

```

**action**

```

$ mysql -h localhost -u dev -p'dEv#1234' app -e "SHOW CREATE TABLE app.t_app_pdf_meta_acc\G" 2>&1
mysql: [Warning] Using a password on the command line interface can be insecure.
*************************** 1. row ***************************
       Table: t_app_pdf_meta_acc
Create Table: CREATE TABLE `t_app_pdf_meta_acc` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `file_name` varchar(200) NOT NULL COMMENT '文件名',
  `file_path` varchar(300) NOT NULL COMMENT '文件绝对路径',
  `file_size_bytes` bigint DEFAULT NULL COMMENT '文件大小，单位字节',
  `is_corrupted` tinyint(1) DEFAULT NULL COMMENT '是否损坏，0：正常，1：损坏',
  `page_count` bigint DEFAULT NULL COMMENT '页数',
  `error_type` varchar(500) DEFAULT NULL COMMENT '错误类型',
  `validation_details_header_valid` tinyint(1) DEFAULT NULL,
  `validation_details_footer_valid` tinyint(1) DEFAULT NULL,
  `validation_details_page_content_valid` tinyint(1) DEFAULT NULL,
  `validation_details_metadata_consistent` tinyint(1) DEFAULT NULL,
  `validation_details_structure_intact` tinyint(1) DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `created_by` char(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '' COMMENT '创建人员',
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `updated_by` char(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT '' COMMENT '更新人员',
  PRIMARY KEY (`id`),
  KEY `idx_updated_at` (`updated_at`),
  KEY `idx_file_name` (`file_name`),
  KEY `idx_file_size_bytes` (`file_size_bytes`),
  KEY `idx_page_count` (`page_count`)
) ENGINE=InnoDB AUTO_INCREMENT=2290 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci

```