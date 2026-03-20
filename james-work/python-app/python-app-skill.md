## python-app

### milvus检索服务

```

在 /Users/Shared/_AllDocMap/02_Project/github/opencode/james-work/python-app/ 目录下，新建 app_milvus_search_api.py 文件，实现一个 FastAPI 服务，支持 数据库、collection_name、search_word 作为参数，返回检索结果。该服务通过 18012 端口提供服务。在接收请求时，需要对参数进行基于 token 的校验；token 的申请方式，通过该服务的另外一个接口获取，接口的地址为：http://localhost:18012/get_token，返回的 token 格式为：{"token": "<PASSWORD>"}， token 的有效期为 24小时，获取 token 的参数为，需要合法的 AK SK。

python 环境使用：/Users/Shared/_AllDocMap/02_Project/gitee/james-python/.conda/bin/python

```

```

根据 /Users/Shared/_AllDocMap/02_Project/github/opencode/james-work/python-app/app_milvus_search_api.py ，实现一个名为 app_milvus_search_client.py 的客户端，实现从 通过 AK SK 申请 token、通过 token 检索数据库、collecton 信息、通过关键字检索数据。这3个功能封装在3个函数中，在 main() 函数中，将3个接口串联起来

```

```

修改 /Users/Shared/_AllDocMap/02_Project/github/opencode/james-work/python-app/app_milvus_search_api.py 和 /Users/Shared/_AllDocMap/02_Project/github/opencode/james-work/python-app/app_milvus_search_client.py，使得客户端请求服务的整个流程能够跑通


```