# 子代理递归派发违规分析报告

## 问题描述

子代理违反了递归保护规则，继续派发了子代理，导致主会话一直等待。

## 违规位置分析

### 1. workflow.md 中的规则定义

**位置**: `.trellis/workflow.md:197`

```markdown
**Sub-agent self-exemption**: if you are already running as `trellis-implement`, 
implement directly from the loaded task context and do NOT spawn another 
`trellis-implement`; if you are already running as `trellis-check`, review/fix 
directly and do NOT spawn another `trellis-check`. The default dispatch rule 
applies to the main session only.
```

**规则说明**:
- `trellis-implement` 子代理不能再派发 `trellis-implement` 或 `trellis-check`
- `trellis-check` 子代理不能再派发 `trellis-check` 或 `trellis-implement`
- 只有主会话可以派发子代理

### 2. 派发协议要求

**位置**: `.trellis/workflow.md:198`

```markdown
**Sub-agent dispatch protocol (all platforms, all sub-agents EXCEPT trellis-research)**: 
When you spawn `trellis-implement` / `trellis-check`, your dispatch prompt **MUST** 
start with one line: `Active task: <task path from \`task.py current\`>`. No exceptions.
```

**协议要求**:
- 所有子代理派发（除了 `trellis-research`）必须在 prompt 开头声明 `Active task: <task path>`
- 派发时必须明确告知被派发的代理，它已经是子代理，不能再派发

### 3. 具体派发点位置

#### 3.1 Phase 2.1 实现阶段

**位置**: `.trellis/workflow.md:447-449`

```markdown
- **Agent type**: `trellis-implement`
- **Task description**: Implement the requirements per prd.md, consulting materials 
  under `{TASK_DIR}/research/`; finish by running project lint and type-check
- **Dispatch prompt guard**: Tell the spawned agent it is already the `trellis-implement` 
  sub-agent and must implement directly, not spawn another `trellis-implement` / `trellis-check`.
```

**违规风险**: 如果主会话没有在 dispatch prompt 中明确声明 "你已经是 `trellis-implement`"，子代理可能会误认为自己是主会话，继续派发。

#### 3.2 Phase 2.2 检查阶段

**位置**: `.trellis/workflow.md:501-503`

```markdown
- **Agent type**: `trellis-check`
- **Task description**: Review all code changes against spec and prd; fix any findings 
  directly; ensure lint and type-check pass
- **Dispatch prompt guard**: Tell the spawned agent it is already the `trellis-check` 
  sub-agent and must review/fix directly, not spawn another `trellis-check` / `trellis-implement`.
```

**违规风险**: 同上，缺少明确的身份声明会导致递归派发。

#### 3.3 brainstorm 技能中的 research 派发

**位置**: `.claude/skills/trellis-brainstorm/SKILL.md:209-237`

```markdown
For each research topic, **spawn a `trellis-research` sub-agent via the Task tool** — 
don't do WebFetch / WebSearch / `gh api` inline in the main conversation.

Agent type: `trellis-research`
Task description template: "Research <specific question>; persist findings to 
`{TASK_DIR}/research/<topic-slug>.md`."
```

**特殊说明**: `trellis-research` 不需要 `Active task:` 前缀，因为它不绑定任务。但它仍然不应该再派发其他子代理。

## 违规检测清单

### 主会话派发时必须做到：

- [ ] 在 dispatch prompt 开头声明 `Active task: <task path>`（除了 `trellis-research`）
- [ ] 明确告知子代理：`You are already running as trellis-implement/trellis-check, do NOT spawn another sub-agent`
- [ ] 使用 **Dispatch prompt guard** 模式

### 子代理必须遵守：

- [ ] `trellis-implement` 检查自己是否是子代理，如果是，直接实现，不派发
- [ ] `trellis-check` 检查自己是否是子代理，如果是，直接检查，不派发
- [ ] `trellis-research` 不派发任何子代理（包括其他 `trellis-research`）

## 违规代码模式

### ❌ 错误模式 1: 子代理继续派发

```markdown
<!-- 在 trellis-implement 子代理内部 -->
I need to implement feature X. Let me spawn a trellis-implement sub-agent to do this.

Agent(
  subagent_type="trellis-implement",
  prompt="Implement feature X"
)
```

**问题**: `trellis-implement` 子代理没有意识到自己已经是子代理，继续派发。

### ❌ 错误模式 2: 主会话派发时缺少身份声明

```markdown
<!-- 在主会话中 -->
Agent(
  subagent_type="trellis-implement",
  prompt="Implement the requirements per prd.md"
)
```

**问题**: 缺少 `Active task:` 前缀和身份声明，子代理无法识别自己的角色。

### ✅ 正确模式: 主会话派发

```markdown
<!-- 在主会话中 -->
Agent(
  subagent_type="trellis-implement",
  prompt="""Active task: .trellis/tasks/06-06-fix-hello-demo

You are already running as the trellis-implement sub-agent. Implement directly 
from the loaded task context. Do NOT spawn another trellis-implement or trellis-check.

Implement the requirements per prd.md, consulting materials under research/; 
finish by running project lint and type-check."""
)
```

### ✅ 正确模式: 子代理自我检查

```markdown
<!-- 在 trellis-implement 子代理内部 -->
I am already running as trellis-implement sub-agent (per my system prompt).
I will implement directly without spawning another sub-agent.

[proceeds with implementation using Edit/Write/Bash tools]
```

## 修复建议

### 1. 增强主会话的派发协议

在 `.trellis/workflow.md` 的派发协议部分（line 198）增加更严格的模板：

```markdown
**Dispatch prompt template**:

```
Active task: <task-path>

You are the trellis-<implement|check> sub-agent. Implement/review directly.
DO NOT spawn another trellis-implement, trellis-check, or any other sub-agent.

<actual task description>
```
```

### 2. 在子代理定义中增加递归深度检查

如果存在子代理定义文件（如 `~/.claude/subagents/trellis-implement.md`），在其 system prompt 中添加：

```markdown
# Identity

You are a trellis-implement sub-agent spawned by the main session.

# Recursion Protection

**CRITICAL**: You are already a sub-agent. You MUST NOT spawn another sub-agent 
(trellis-implement, trellis-check, trellis-research, or any other Agent tool call).

If you attempt to spawn a sub-agent, you will violate the recursion protection 
and cause the main session to hang indefinitely.

# What to do instead

Implement directly using:
- Read tool (read files)
- Write tool (create files)
- Edit tool (modify files)
- Bash tool (run commands)

Do NOT use the Agent tool under any circumstances.
```

### 3. 在 workflow.md 的 self-exemption 规则中增加检测逻辑

在 `.trellis/workflow.md:197` 之后添加：

```markdown
**Recursion detection**: Sub-agents can detect their identity by checking:
- System prompt contains "You are the trellis-implement sub-agent" or similar
- Environment variable `TRELLIS_AGENT_DEPTH` > 0 (if implemented)
- The dispatch prompt started with "Active task:" followed by identity statement

If any of these conditions are true, the agent MUST NOT spawn another sub-agent.
```

### 4. 添加环境变量传递机制（可选）

如果平台支持，可以在派发时设置环境变量：

```bash
TRELLIS_AGENT_DEPTH=1  # 主会话派发子代理时设置为 1
TRELLIS_AGENT_TYPE=trellis-implement  # 声明代理类型
```

子代理检查：
```python
import os
if int(os.getenv('TRELLIS_AGENT_DEPTH', '0')) > 0:
    # I am a sub-agent, do not spawn
    pass
```

## 总结

**违规根因**:
1. 子代理缺少递归深度的自我意识
2. 主会话派发时没有明确声明子代理身份
3. 缺少强制的递归保护检查机制

**修复优先级**:
1. **P0**: 在 workflow.md 中增强派发协议模板（立即生效）
2. **P1**: 在子代理定义中添加递归保护说明（需要更新代理定义）
3. **P2**: 添加环境变量检测机制（需要平台支持）

**验证方法**:
- 检查所有 Agent tool 调用是否包含身份声明
- 在子代理中搜索 `Agent(` 或 `subagent_type` 关键词，确认是否有违规派发
- 添加单元测试，验证子代理不会再次调用 Agent 工具
