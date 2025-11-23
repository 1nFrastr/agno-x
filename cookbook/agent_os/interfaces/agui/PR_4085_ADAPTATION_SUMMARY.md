# PR #4085 适配总结

## 概述

本次工作将 PR #4085（人工干预确认功能）适配到当前最新版本的 Agno 框架。该PR最初在几个月前提出，期间框架经历了多次版本升级，需要重新适配。

## PR #4085 的核心功能

PR #4085 为 Agno 框架添加了人工干预（Human-in-the-Loop）确认功能，通过 AG-UI 协议实现：

1. **工具标记**：工具可以被标记为需要用户确认（`requires_confirmation=True`）
2. **暂停执行**：当遇到需要确认的工具时，Agent 暂停执行
3. **状态快照**：生成 `StateSnapshotEvent`，状态为 `paused_for_confirmation`
4. **继续执行**：用户确认后，通过 `continue_run` 继续执行

## 已完成的适配工作

### 1. 修改 `libs/agno/agno/os/interfaces/agui/router.py`

在 `run_agent` 函数中添加了对暂停状态的检测和处理：

```python
# 检测是否是从暂停状态继续
if (
    hasattr(run_input, "state")
    and run_input.state
    and isinstance(run_input.state, dict)
    and run_input.state.get("status") == "paused_for_confirmation"
):
    # 从暂停状态继续，使用 acontinue_run
    from agno.models.response import ToolExecution
    
    updated_tools = [ToolExecution.from_dict(t) for t in run_input.state.get("tools_to_confirm", [])]
    
    response_stream = agent.acontinue_run(
        run_id=run_id,
        updated_tools=updated_tools,
        session_id=run_input.thread_id,
        stream=True,
        stream_events=True,
        user_id=user_id,
    )
else:
    # 正常启动新的运行
    response_stream = agent.arun(...)
```

### 2. 修改 `libs/agno/agno/os/interfaces/agui/utils.py`

#### 2.1 添加 StateSnapshotEvent 导入

```python
from ag_ui.core import (
    BaseEvent,
    CustomEvent,
    EventType,
    RunFinishedEvent,
    StateSnapshotEvent,  # 新增
    ...
)
```

#### 2.2 修改 `_create_completion_events` 函数

在处理 `RunPausedEvent` 时，检测需要确认的工具并生成 `StateSnapshotEvent`：

```python
if isinstance(chunk, RunPausedEvent) and chunk.tools is not None:
    # 检查是否有需要确认的工具
    tools_requiring_confirmation = [t for t in chunk.tools if t.requires_confirmation]
    
    if tools_requiring_confirmation:
        # 生成 StateSnapshotEvent
        tools_to_confirm = [t.to_dict() for t in tools_requiring_confirmation]
        state_snapshot = {
            "status": "paused_for_confirmation",
            "tools_to_confirm": tools_to_confirm,
        }
        snapshot_event = StateSnapshotEvent(type=EventType.STATE_SNAPSHOT, snapshot=state_snapshot)
        events_to_emit.append(snapshot_event)
        
        # 提前返回，不发送 RunFinishedEvent
        return events_to_emit
```

## 创建的测试和示例

### 1. `cookbook/agent_os/interfaces/agui/human_in_the_loop_confirmation.py`

完整的 AGUI 服务器示例，展示：
- 需要确认的工具（发送邮件、删除文件）
- 不需要确认的工具（查询天气）
- 完整的 AgentOS 配置

运行方式：
```bash
python cookbook/agent_os/interfaces/agui/human_in_the_loop_confirmation.py
```

访问：http://localhost:9002

### 2. `cookbook/agent_os/interfaces/agui/test_hitl_confirmation.py`

自动化测试脚本，验证：
- StateSnapshotEvent 的生成
- 暂停和继续流程
- 确认工具的执行
- 非确认工具的直接执行

运行方式：
```bash
python cookbook/agent_os/interfaces/agui/test_hitl_confirmation.py
```

### 3. `cookbook/agent_os/interfaces/agui/HITL_README.md`

详细文档，包含：
- 功能概述
- 使用方法
- 架构说明
- 实现细节
- 测试指南

## 与原始 PR 的主要差异

1. **API 变化**：
   - 原 PR 使用 `arun(..., run_id=run_id)`
   - 当前版本直接使用 `acontinue_run(run_id=...)`

2. **事件流**：
   - 原 PR 中事件处理较简单
   - 当前版本使用 `stream_events=True` 和更复杂的事件缓冲机制

3. **状态检测**：
   - 添加了更严格的类型检查（`isinstance(run_input.state, dict)`）
   - 改进了错误处理

4. **完整性**：
   - 不仅生成 StateSnapshotEvent，还确保不发送 RunFinishedEvent
   - 完整的事件流控制（提前返回）

## 测试方法

### 自动化测试
```bash
cd cookbook/agent_os/interfaces/agui
python test_hitl_confirmation.py
```

预期输出：
- ✓ StateSnapshotEvent 正确生成
- ✓ 工具确认和继续执行正常
- ✓ 非确认工具直接执行

### 手动测试
1. 启动服务器：`python human_in_the_loop_confirmation.py`
2. 在浏览器中打开 AGUI 界面
3. 发送需要确认的请求："Send an email to test@example.com"
4. 观察暂停和确认请求
5. 确认后观察执行完成

## 集成指南

要在现有 Agent 中使用此功能：

```python
from agno.tools import tool

@tool(requires_confirmation=True)
def sensitive_operation(param: str) -> str:
    """需要用户确认的敏感操作"""
    return f"执行了敏感操作: {param}"

# 使用 AGUI 接口
from agno.os import AgentOS
from agno.os.interfaces.agui import AGUI

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[sensitive_operation],
)

agent_os = AgentOS(
    agents=[agent],
    interfaces=[AGUI(agent=agent)],
)
```

## 注意事项

1. **依赖项**：需要 `ag-ui-protocol` 库支持 `StateSnapshotEvent`
2. **兼容性**：此实现与当前框架的 `continue_run` API 兼容
3. **向后兼容**：不影响不使用确认功能的现有代码
4. **团队支持**：当前实现仅支持 Agent，Team 支持待后续添加

## 后续工作建议

1. 为 Team 添加类似的确认支持
2. 添加更多单元测试
3. 考虑超时机制（暂停状态的有效期）
4. 添加确认历史记录
5. 支持批量确认多个工具

## 参考资料

- [原始 PR #4085](https://github.com/agno-agi/agno/pull/4085)
- [AG-UI 协议文档](https://docs.ag-ui.com/concepts/state#human-in-the-loop-collaboration)
- [Agno 框架测试](libs/agno/tests/integration/agent/test_user_confirmation_flows.py)
