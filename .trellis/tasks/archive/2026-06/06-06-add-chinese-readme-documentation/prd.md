# Add Chinese README Documentation

## Goal

为 issue-codex-automation 项目创建中文版使用说明文档（README.zh-CN.md），帮助中文用户更好地理解和使用该工具。

## What I Already Know

* 现有英文 README.md 长度约 307 行，结构完整
* 主要章节包括：Overview, Installation, Configuration, Usage, Commands, Safety Features, Troubleshooting 等
* 项目是一个 GitHub issue 驱动的代码自动化工具
* 工具使用 Python 开发，通过 CLI 命令交互
* 目标用户是需要自动化处理 GitHub issue 的开发者

## Assumptions (Temporary)

* 中文文档应保持与英文文档相同的结构
* 需要翻译所有章节内容
* 代码示例和命令保持英文原样
* 技术术语需要合理处理（保留英文或提供中英对照）

## Requirements

* 创建 README.zh-CN.md 文件
* 翻译所有主要章节标题和内容
* 保持原有文档结构和层级
* 保留代码示例和命令本身，但翻译其中的注释
* **翻译风格**：中文为主，关键技术术语首次出现时标注英文（如"议题（issue）"），后续直接使用中文
* **代码注释处理**：翻译所有代码块中的注释（如 `# Required` → `# 必需`）
* 确保中文表达自然流畅，符合技术文档规范
* 在英文 README 顶部添加中文文档链接

## Acceptance Criteria

* [ ] README.zh-CN.md 文件创建完成
* [ ] 所有章节内容翻译完整（Overview, Installation, Configuration, Usage, Commands, Safety Features, Troubleshooting 等）
* [ ] 代码示例中的注释已翻译成中文
* [ ] 关键技术术语首次出现时已标注英文
* [ ] 中文表达准确、专业、自然
* [ ] 英文 README 顶部添加了中文文档链接

## Definition of Done (Team Quality Bar)

* 翻译内容准确，无遗漏章节
* 技术术语使用规范统一
* 文档格式符合 Markdown 规范
* 代码块和命令示例保持可复制性
* 经过人工审阅（如需要）

## Technical Approach

1. 创建 README.zh-CN.md 文件
2. 按章节翻译内容，保持原有结构
3. 翻译代码注释，保留命令和代码本身
4. 在英文 README 顶部添加语言切换链接（如：`[English](README.md) | [简体中文](README.zh-CN.md)`）

## Implementation Plan

* PR1: 创建并翻译 README.zh-CN.md + 在英文 README 添加链接

## Out of Scope (Explicit)

* 不翻译其他文档文件（如 AGENTS.md, CONTRIBUTING.md 等）
* 不修改英文 README 的内容
* 不创建其他语言版本的文档
* 不添加英文文档中没有的额外内容

## Technical Notes

* 主文件：`/Users/zhqxiang/application/agent/lab/README.md` (307 行)
* 目标文件：`/Users/zhqxiang/application/agent/lab/README.zh-CN.md`
* 项目使用 Python + GitHub API
* 关键术语：issue, label, prompt, state, eligible, goal prompt, safe-mode
