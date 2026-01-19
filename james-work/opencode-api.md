## Python 代码

[app_opn_call_by_http.py](https://gitee.com/james-hadoop/python-app/blob/main-macos/app/open_code/app_opn_call_by_http.py)


## API 调试过程

### prompt

```

如何通过 api 调用 opencode 中的 models？给出一个可以在本机上运行的  curl 示例

```

### 使用示例

根据 opencode 的 API，这里是如何通过 API 调用 models 的 curl 示例：

1. 首先列出所有可用的 providers 和 models

```

curl http://localhost:4096/provider

```

2. 创建一个 session

```

curl -X POST http://localhost:4096/session \
  -H "Content-Type: application/json" \
  -d '{}'

```

```json

{
  "id": "ses_42c8718b2ffe4VDu9XKu1JDQwE",
  "slug": "lucky-comet",
  "version": "local",
  "projectID": "4b0ea68d7af9a6031a7ffda7ad66e0cb83315750",
  "directory": "/Users/Shared/_AllDocMap/02_Project/github/opencode/packages/opencode",
  "title": "New session - 2026-01-18T23:28:26.793Z",
  "time": { "created": 1768778906793, "updated": 1768778906793 }
}

```


3. 向 session 发送消息并使用指定的 model
# 假设 session ID 是从步骤2返回的 "ses_42c8718b2ffe4VDu9XKu1JDQwE"

```

curl -s -w "\nHTTP Status: %{http_code}\n" -X POST http://localhost:4096/session/ses_42c8718b2ffe4VDu9XKu1JDQwE/message \
  -H "Content-Type: application/json" \
  -d '{
    "model": {
      "providerID": "opencode",
      "modelID": "glm-4.7-free"
    },
    "parts": [
      {
        "type": "text",
        "text": "比较一下 claud code 与 opencode 的优缺点"
      }
    ]
  }'

```


4. 获取 session 的消息历史

```

curl http://localhost:4096/session/ses_42c8718b2ffe4VDu9XKu1JDQwE/message

```

关键参数说明：
- providerID: 从 /provider 端点获取，如 "opencode", "openai", "anthropic" 等
- modelID: 具体的模型 ID，如 "gpt-4o", "claude-3-5-sonnet" 等
- parts: 消息内容数组，支持文本和文件类型
- 服务器默认运行在 http://localhost:4096

```

