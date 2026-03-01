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