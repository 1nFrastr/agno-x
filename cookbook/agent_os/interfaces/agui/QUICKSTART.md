# 快速开始指南：人工干预确认 (HITL)

## 5分钟快速上手

### 1. 定义需要确认的工具

```python
from agno.tools import tool

@tool(requires_confirmation=True)
def send_email(to: str, subject: str, body: str) -> str:
    """发送邮件 - 需要用户确认"""
    return f"Email sent to {to}"
```

### 2. 创建带 AGUI 接口的 Agent

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.os import AgentOS
from agno.os.interfaces.agui import AGUI

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[send_email],
)

agent_os = AgentOS(
    agents=[agent],
    interfaces=[AGUI(agent=agent)],
)
app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve(app="your_file:app", port=9001)
```

### 3. 运行并测试

```bash
# 启动服务器
python your_file.py

# 在浏览器中打开 AGUI 界面
# 发送请求："Send an email to test@example.com"
# 观察确认流程
```

## 测试示例

### 运行现有示例

```bash
cd cookbook/agent_os/interfaces/agui

# 完整服务器示例
python human_in_the_loop_confirmation.py

# 简单测试（无需服务器）
python simple_hitl_test.py

# 完整 AGUI 协议测试
python test_hitl_confirmation.py
```

## 工作原理

```
用户: "Send an email to john@example.com"
  ↓
Agent 检测到需要确认
  ↓
暂停并发送 StateSnapshotEvent
  ↓
前端显示确认对话框
  ↓
用户点击"确认"
  ↓
Agent 继续执行
  ↓
邮件发送成功
```

## 核心概念

### 工具标记
```python
@tool(requires_confirmation=True)  # 需要确认
def sensitive_action(): ...

@tool  # 不需要确认（默认）
def safe_action(): ...
```

### 状态快照
```json
{
  "status": "paused_for_confirmation",
  "tools_to_confirm": [
    {
      "tool_name": "send_email",
      "tool_args": {"to": "john@example.com", ...},
      "confirmed": false
    }
  ]
}
```

### 继续执行
```python
# 前端确认后
tools[0]["confirmed"] = True

# 发送继续请求
RunAgentInput(
    run_id=original_run_id,
    thread_id=original_thread_id,
    state={
        "status": "paused_for_confirmation",
        "tools_to_confirm": tools
    }
)
```

## 常见用例

### 1. 敏感操作
```python
@tool(requires_confirmation=True)
def delete_file(filename: str):
    """删除文件"""
    ...

@tool(requires_confirmation=True)
def transfer_money(amount: float, to_account: str):
    """转账"""
    ...
```

### 2. 成本控制
```python
@tool(requires_confirmation=True)
def call_expensive_api(data: dict):
    """调用昂贵的 API"""
    ...
```

### 3. 合规性
```python
@tool(requires_confirmation=True)
def access_sensitive_data(user_id: str):
    """访问敏感数据 - 需要审计跟踪"""
    ...
```

## 文档链接

- [详细文档](./HITL_README.md)
- [实现总结](./PR_4085_ADAPTATION_SUMMARY.md)
- [完整报告](./IMPLEMENTATION_REPORT.md)

## 常见问题

**Q: 如何禁用确认？**
A: 不使用 `requires_confirmation=True` 参数即可。

**Q: 可以在确认时修改参数吗？**
A: 可以！在前端修改 `tool_args` 后再确认。

**Q: 支持批量确认吗？**
A: 当前需要逐个确认，批量确认功能在开发计划中。

**Q: 确认超时怎么办？**
A: 当前没有超时机制，需要手动处理或在后续版本中添加。

## 下一步

- ✅ 查看完整示例：`human_in_the_loop_confirmation.py`
- ✅ 运行测试：`simple_hitl_test.py`
- ✅ 阅读详细文档：`HITL_README.md`
- ✅ 了解实现细节：`PR_4085_ADAPTATION_SUMMARY.md`
