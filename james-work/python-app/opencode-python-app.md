### 目录

- [数据库读写](#数据库读写)
- [python-app风格重写代码](#python-app风格重写代码)

### 数据库读写

**prompt**

```

增强  /Users/Shared/_AllDocMap/02_Project/gitee/python-app/app_local/toutiao/app_toutiao_scraper_auto.py 的功能，将获取到的内容写入到数据表 app.t_app_toutiao_article_acc 中。

用 code-reviewer-agent review 代码和逻辑功能，如果功能符合预期则测试通过；如果功能有bug，通过 python-agent 修复 bug再提测。循环上述过程 3 次

参考 /Users/Shared/_AllDocMap/02_Project/gitee/python-app/app_local/article/app_article_pdf_meta.py 中的代码 片段：DataWriteUtil.write_to_db_with_create_info(df, "t_app_pdf_meta_acc", config.get_db_connection_string()) 

将 /Users/Shared/_AllDocMap/02_Project/github/opencode/packages/opencode/toutiao_scraper.py 修改成通过读取配置文件以及调用 python 库，实现写入数据到 mysql 表：app.t_app_toutiao_article_acc definition

```

**action**

[toutiao_scraper.py](./toutiao_scraper.py)

### python-app风格重写代码


```

在保证 /Users/Shared/_AllDocMap/02_Project/github/opencode/packages/opencode/toutiao_scraper.py 功能不变的前提下，将代码风格改写成 /Users/Shared/_AllDocMap/02_Project/gitee/python-app/app_local/article/app_article_pdf_meta.py 的样式，main 函数要调用以下代码来出来业务逻辑，方便不同 app 的统一抽象。     processor=Processor(process=lambda: process(config, dt))
    processor.do_process()

```  

**action**

[toutiao_scraper.py](./toutiao_scraper.py)


**prompt**

```

增强 /Users/Shared/_AllDocMap/02_Project/github/opencode/james-work/python-app/app_article_toutiao_scraper.py 的功能，使得程序能够自动抓取今日头条 财经、科技、国际、上海、深圳、杭州最热最新的 20 篇文章。python 环境使用：/Users/Shared/_AllDocMap/02_Project/gitee/james-python/.conda/bin/python 。用 code-reviewer-agent review 代码和逻辑功能，如果功能符合预期则测试通过；如果功能有bug，通过 python-agent 修复 bug再提测。循环上述过程 3 次

```

