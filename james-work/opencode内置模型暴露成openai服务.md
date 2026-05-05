### HTTP 请求

#### FastAPI代码路径

[FastAPI代码](/Users/Shared/_AllDocMap/02_Project/gitee/python-app/app_local/open_code/main.py)

#### POST请求

```

http://127.0.0.1:4096/session/ses_37332f949ffeffsHB9JMryLiLq/prompt_async


```

#### Payload

```

{
  "agent": "build",
  "model": { "modelID": "minimax-m2.5-free", "providerID": "opencode" },
  "messageID": "msg_c8ccd06ca0018x4VMX5z3AwAXa",
  "parts": [
    {
      "id": "prt_c8ccd06ca002lamaPJFM7LccLz",
      "type": "text",
      "text": "在 /Users/Shared/_AllDocMap/02_Project/gitee/python-app/app_local/open_code 目录下，用 fastapi 实现功能：将 opencode 中的 minimax/minimax-m2.5 模型，通过 openai 的方式提供 http 服务"
    }
  ]
}

```

#### Curl调用

```

curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "minimax-m2.5-free", "messages": [{"role": "user", "content": "今天上海的日期和天气情况"}]}'

```  
