## Milvus 环境

### Milvus

```

修改 /Users/Shared/_AllDocMap/02_Project/github/opencode/james-work/milvus/docker-compose.yml ，满足以下要求：

1. milvus 容器的名称为 james-milvus，管理员账号为 root，密码为 RoOt#1234
2. milvus 数据存储在 /Volumes/james1t/_AllDocMap/_DATA/milvus 目录下
3. 使用的 minio 容器的名称为 james-minio，工作的端口号为：19000
4. minio 数据存储在 /Volumes/james1t/_AllDocMap/_DATA/minio 目录下
5. 使用的 etcd 容器的名称为 james-etcd
6. etcd 数据存储在 /Volumes/james1t/_AllDocMap/_DATA/etcd 目录下

```

```

使用 /Users/Shared/_AllDocMap/02_Project/github/opencode/james-work/milvus/docker-compose.yml，启动 milvus 容器

```


### Attr

```

根据 /Users/Shared/_AllDocMap/02_Project/github/opencode/james-work/milvus/docker-compose.yml 的配置信息，以及以下 attr 容器的运行命令，在 /Users/Shared/_AllDocMap/02_Project/github/opencode/james-work/attu/ 目录下，新建 attr 的 docker-compose.yml 文件

docker run -d \
--name james-attu \
-p 18002:3000 \
--network milvus_default \
-e MILVUS_URL=milvus-milvus-1:19530 \
zilliz/attu:v2.6.5 

```

## 代码功能

### content_list

```

完善 /Users/Shared/_AllDocMap/02_Project/github/opencode/james-work/milvus/app_article_content_list_getter.py 中 read_content_from_content_list_file 函数的能力：入参文件是一个 json 文件，将 json 中 "type": "text" 的 所有 "text" 值提取出来，合并成一个字符串，用空格连接

```

```

增强 /Users/Shared/_AllDocMap/02_Project/github/opencode/james-work/milvus/app_article_content_list_getter.py 中 chuck_content_by_size 函数的能力：按指定大小切分成多个子字符串

```

```

将 /Users/Shared/_AllDocMap/02_Project/github/opencode/james-work/milvus/milvus_search_with_file_path_demo.py 中的 search_with_file_path(search_word) 代码片段该写成独立的 python 代码文件。增强新生成的代码文件的功能，支持检索最相关的 n 条数据，这个 n 作为入参传入

```

```

完善 /Users/Shared/_AllDocMap/02_Project/github/opencode/james-work/milvus/app_article_content_list_getter.py 中 read_content_list_from_content_list_file 函数的能力：入参文件是一个 json 文件，将 json 中 "type": "text" 且 "text" 值的长度大于 5 的 所有 "text" 值提取出来，将提取出来的值中的换行符替换成硬编码：CH_NL，合并成一个字符串列表，返回

```

```

增强 /Users/Shared/_AllDocMap/02_Project/github/opencode/james-work/milvus/app_milvus_search_with_n.py 的功能，将检索结果中最相关的 n 条数据，根据 file_path 进行合并，按照 file_path 出现的频次从高到低排序，输入 file_path 以及对应的频次

```

```

新建一个 python 文件，将 /Users/Shared/_AllDocMap/02_Project/github/opencode/james-work/milvus/app_milvus_search_with_n.py 的功能封装成一个 FastAPI 服务，暴露 GET 方法，通过 18011 端口提供服务。

完成上述步骤之后，写入调用该服务的客户端 python 代码；并给出对应的 curl 命令调用方法

```

```

增强 /Users/Shared/_AllDocMap/02_Project/github/opencode/james-work/milvus/milvus_search_api.py 的功能，@app.get("/search") 方法支持指定数据库和 collection_name

```


## 用户使用

```

根据 http://localhost:18011/docs 的 API 信息，查询：观测质量管理体系的内审要求有哪些

```

```

根据 http://localhost:18011/docs 的 API 信息，查询：观测质量管理体系的内审要求有哪些？

注意：检索出 30 条结果之后，用50个字精炼之后再返回答案，同时给出答案出处的文件路径

```

```

调用本地 API http://localhost:18011/search?q=观测质量管理体系的内审要求有哪些，在不查阅互联网资料的前提下，检索出 30 条结果之后，用50个字精炼之后再返回答案，同时给出答案出处的文件路径，文件路径的字段是：file_path

```