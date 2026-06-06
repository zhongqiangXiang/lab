# issue-codex-automation

[English](README.md) | 简体中文

GitHub 议题（issue）驱动的 Codex 自动化工具，用于从仓库议题安全、可控地生成代码。

## 概述

`issue-codex-automation` 监视你 GitHub 仓库中的议题，检测新的可执行议题，并生成目标提示词（goal prompt），这些提示词可以通过 [Codex](https://github.com/anthropics/codex) 执行以实现所请求的更改。

**主要特性**：
- 基于标签（label）的议题准入控制（默认：`codex-ready`）
- 安全模式 MVP：生成提示词供手动审核后再执行
- 本地状态跟踪以避免重复处理
- 仅使用标准库构建（无外部依赖）

## 安装

```bash
# 从仓库根目录
pip install -e .

# 验证安装
issue-codex-automation --version
```

## 配置

在你的仓库根目录创建 `.env` 文件：

```bash
# 必需
GITHUB_TOKEN=ghp_xxxxxxxxxxxxx

# 可选 - 如果未设置则从 git remote 自动检测
GITHUB_REPO=owner/repo

# 可选默认值
STATE_DIR=.codex_issue_agent
LABEL_FILTER=codex-ready
INCLUDE_COMMENTS=false
```

### 配置参考

| 变量 | 必需 | 默认值 | 描述 |
|----------|----------|---------|-------------|
| `GITHUB_TOKEN` | 是 | - | 具有 repo 作用域的 GitHub 个人访问令牌 |
| `GITHUB_REPO` | 否 | 自动检测 | 仓库格式为 `owner/repo` |
| `STATE_DIR` | 否 | `.codex_issue_agent` | 状态和运行产物的目录 |
| `LABEL_FILTER` | 否 | `codex-ready` | 议题准入所需的标签 |
| `INCLUDE_COMMENTS` | 否 | `false` | 在生成的提示词中包含议题评论 |

### 获取 GitHub 令牌

1. 前往 GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. 生成具有 `repo` 作用域的新令牌（或仅公共仓库使用 `public_repo`）
3. 复制令牌并添加到 `.env`

## 使用

### 工作流概述

```bash
# 步骤 1：发现新的符合条件的议题
issue-codex-automation check

# 步骤 2：为特定议题生成目标提示词
issue-codex-automation generate <issue-number>

# 步骤 3：审查生成的提示词
cat .codex_issue_agent/runs/issue-<N>/goal.md

# 步骤 4：使用 Codex 执行（手动步骤）
codex exec -C . - < .codex_issue_agent/runs/issue-<N>/goal.md
```

### 命令

#### `check` - 发现符合条件的议题

从 GitHub 获取开放的议题并更新本地状态。

```bash
issue-codex-automation check [--since TIMESTAMP] [--force-refresh]
```

**选项**：
- `--since TIMESTAMP`：使用 ISO-8601 时间戳覆盖 `last_seen_at`
- `--force-refresh`：忽略 `last_seen_at`，获取所有开放的议题

**输出**：包含编号、标题、标签和 URL 的新议题表格

**退出码**：
- `0`：成功
- `1`：配置错误（缺少 `GITHUB_TOKEN`，仓库无效）
- `2`：GitHub API 错误（认证失败、速率限制、网络问题）
- `3`：状态文件错误（损坏、权限被拒绝）

**示例**：

```bash
$ issue-codex-automation check

INFO: Fetching open issues from owner/repo...
INFO: Found 3 eligible issues

New eligible issues:
----------------------------------------------------------------------------------------------------
#        Title                                              Labels               URL
----------------------------------------------------------------------------------------------------
123      Add user authentication                            codex-ready, feat... https://github.com/...
124      Fix memory leak in parser                          codex-ready, bug     https://github.com/...
125      Update README                                      codex-ready, docs    https://github.com/...
----------------------------------------------------------------------------------------------------
Total: 3 issues
```

#### `generate` - 生成目标提示词

为特定议题创建目标提示词文件。

```bash
issue-codex-automation generate <issue-number> [--force] [--no-comments]
```

**参数**：
- `issue-number`：GitHub 议题编号（必需）

**选项**：
- `--force`：如果存在则覆盖现有的 `goal.md`
- `--no-comments`：跳过获取评论（覆盖 `INCLUDE_COMMENTS`）

**输出**：
- `.codex_issue_agent/runs/issue-<N>/goal.md`：生成的提示词
- `.codex_issue_agent/runs/issue-<N>/metadata.json`：议题元数据
- 打印要运行的 `codex exec` 命令

**退出码**：
- `0`：成功
- `1`：配置错误
- `2`：GitHub API 错误
- `3`：状态文件错误
- `4`：议题不符合条件（缺少标签、已生成、是 PR）
- `5`：状态中未找到议题（先运行 `check`）

**示例**：

```bash
$ issue-codex-automation generate 123

INFO: Fetching issue #123 from GitHub...
INFO: Generating goal prompt...

Generated goal prompt: .codex_issue_agent/runs/issue-123/goal.md
Metadata: .codex_issue_agent/runs/issue-123/metadata.json

To execute with Codex, run:
  codex exec -C . - < .codex_issue_agent/runs/issue-123/goal.md
```

### 全局选项

```bash
issue-codex-automation [OPTIONS] COMMAND

Options:
  --config PATH       .env 文件路径（默认：当前目录下的 .env）
  --state-dir PATH    覆盖 STATE_DIR
  --verbose           启用调试日志
  --version           打印版本并退出
```

## 议题准入条件

如果议题满足以下条件，则符合代码生成条件：

1. ✅ 状态为 `open`
2. ✅ 具有配置的标签（默认：`codex-ready`）
3. ✅ 不是拉取请求（pull request）
4. ✅ 存在于本地状态中（运行 `check` 以发现）

### 标签策略

将 `codex-ready` 标签添加到以下议题：
- 需求明确清晰
- 适合自动化实现
- 范围适当（不太宽泛）

这提供了人工审批关口，确保在生成任何目标提示词之前经过审核。

## 状态管理

状态存储在 `STATE_DIR/state.json` 中：

```json
{
  "last_seen_at": "2024-06-05T10:30:00+00:00",
  "issues": {
    "123": {
      "number": 123,
      "title": "Add user authentication",
      "url": "https://github.com/owner/repo/issues/123",
      "labels": ["codex-ready", "feature"],
      "first_seen": "2024-06-05T10:00:00",
      "last_seen": "2024-06-05T10:30:00",
      "generated": true,
      "generated_at": "2024-06-05T10:35:00"
    }
  }
}
```

### 运行产物

每次 `generate` 都会创建一个运行目录：

```
.codex_issue_agent/runs/issue-<N>/
├── goal.md          # 生成的提示词（执行前可编辑）
└── metadata.json    # 议题元数据，用于可审计性
```

## 安全特性

### 安全模式 MVP

MVP 不会自动执行 Codex。相反：
1. `check` 发现符合条件的议题
2. `generate` 创建提示词文件
3. **你审查提示词**
4. **你手动运行 `codex exec`**

这保留了有用的自动化，同时保持人工控制：
- 提示词质量
- 范围验证
- 仓库安全性

### 提示词注入保护

议题正文和评论被视为不可信输入：
- 包裹在围栏代码块中
- 明确指示遵循项目指南而非议题文本
- 对模糊需求设置停止条件

### 验证关卡

`generate` 命令会验证：
- 议题具有必需的标签
- 议题是开放的（未关闭）
- 议题不是拉取请求
- 执行前的工作树状态

## 故障排除

### "GITHUB_TOKEN is required"

在你的 `.env` 文件或环境中设置 `GITHUB_TOKEN`：

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
```

### "Could not detect repository from git remote"

可以：
- 确保 `git remote get-url origin` 指向 GitHub 仓库
- 在 `.env` 中设置 `GITHUB_REPO`：

```bash
GITHUB_REPO=owner/repo
```

### "Authentication failed"

你的 `GITHUB_TOKEN` 无效或缺少必需的权限。生成具有 `repo` 作用域的新令牌。

### "API rate limit exceeded"

GitHub API 速率限制：
- **已认证**：5,000 请求/小时
- **未认证**：60 请求/小时

等待速率限制重置或使用具有更高限制的令牌。

### "Issue not found in state"

首先运行 `check` 以发现并跟踪议题：

```bash
issue-codex-automation check
issue-codex-automation generate <issue-number>
```

## 未来增强

安全模式 MVP 奠定了基础。未来版本可能会添加：

- **自动执行**：`run` 命令直接执行 Codex
- **分支隔离**：为每个议题创建功能分支
- **PR 创建**：成功运行后自动打开拉取请求
- **议题评论**：将状态报告回 GitHub
- **更丰富的路由**：基于标签的代理选择或配置
- **验证钩子**：执行前检查（脏工作树、测试基准）
- **审计日志**：每次运行的详细执行日志

## 许可证

MIT License - 详见 LICENSE 文件
