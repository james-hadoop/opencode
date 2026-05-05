
### openclaw 注册 local-llm 模型

```

根据 http://localhost:18000/v1/models 提供的模型列表，修改 /Users/Shared/_AllDocMap/02_Project/github/openclaw 代码，给 openclaw 注册一个名为 local-llm 的 provide，[Pasted ~6 lines] {
      "id": "minimax-m2.5-free",
      "object": "model",
      "created": 1772969529,
      "owned_by": "opencode"
    }

```


```
openclaw 注册 local-llm 模型时会输入一个 API 密钥：
 How do you want to provide this API key?

在使用 http://127.0.0.1:18000/v1 或者 http://localhost:18000/v1 地址时，提过输入 API 密钥的步骤

将上述功能修改到 /Users/Shared/_AllDocMap/02_Project/github/openclaw 中 

用 code-reviewer-agent review 代码和逻辑功能，如果功能符合预期则测试通过；如果功能有bug，通过 python-agent 修复 bug再提测。循环上述过程 2 次

 ```


 ```

 ⚠️ Agent failed before reply: No API key found for provider "local-llm". Auth store: /Users/james/.openclaw/agents/main/agent/auth-profiles.json (agentDir: /Users/james/.openclaw/agents/main/agent). Configure auth for this agent (openclaw agents add <id>) or copy auth-profiles.json from the main agentDir.
Logs: openclaw logs --follow

```