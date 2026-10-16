# research-to-report-and-briefing

面向技术、产品与产业研究的 Codex 技能，贯通独立调研、技术报告、汇报PPT、逐页演讲稿和作者技术详解，配套项目记忆与质量检查方法。强调证据可追溯、机制可解释、系统逻辑和自然中文表达，支持跨领域适配与持续迭代。

当前版本：**1.2.1**。技能入口为 [SKILL.md](SKILL.md)。

## 适用任务

- 独立开展技术、产品、产业或路线研究，形成有证据支撑的判断。
- 撰写、深化或修订研究报告，解释特色机制、实现细节及系统作用。
- 将报告组织为技术汇报，按需要配套逐页演讲稿和作者学习材料。
- 持续维护成套材料，用辅助文档保存研究主线、来源、决定和检查状态。

成果按任务选择，可以只做研究、报告、局部解释或样稿，也可以制作完整汇报材料。普通单句润色和单一事实查询通常不需要完整流程。

## 方法特点

- **独立取证**：以原始资料、引用追踪和反向核查支撑判断，区分实际阅读、候选线索及作者推理。
- **系统解释**：沿前置知识、表示、操作、状态、跨层接口和系统效果展开，用原图及完整算例解释关键机制。
- **自然表达**：使用领域通行语言，精简空泛过场和重复提示，保留决定结论的条件。
- **可解释汇报**：围绕真实关系组织高信息密度页面，核对图形编码、讲稿语义和讲述节奏。
- **可恢复记录**：用规范、指南、质量、内容、证据和进度六类信息承接长任务；支持合并或分文件维护。
- **实际验证**：关联来源、计算和最终文件身份；按成果格式检查真实页面，修订后复查受影响内容。

## Windows、Linux安装与配置

安装、默认目录和使用方式已于 **2026-10-16** 按官方文档核对。按所用工具选择完整步骤：

- [Codex：Windows原生、Linux及WSL2](docs/setup-codex.md)：CLI安装与登录、默认目录、技能放置、配置、调用、项目记忆助手和更新。
- [Claude Code：Windows原生、Linux及WSL](docs/setup-claude-code.md)：原生安装、用户/项目技能、设置文件、调用与重载、助手和排错。

两套工具的默认用户级技能路径分别为：

| 工具 | Windows原生 | Linux/WSL内部 |
| --- | --- | --- |
| Codex | `%USERPROFILE%\.agents\skills\research-to-report-and-briefing\` | `~/.agents/skills/research-to-report-and-briefing/` |
| Claude Code | `%USERPROFILE%\.claude\skills\research-to-report-and-briefing\` | `~/.claude/skills/research-to-report-and-briefing/` |

Codex的用户配置文件仍为`~/.codex/config.toml`，与当前技能目录不同。Claude Code的用户设置文件为`~/.claude/settings.json`。Windows的用户主目录通常为`C:\Users\<用户名>`；WSL使用Linux发行版自己的用户主目录。[Codex官方目录](https://learn.chatgpt.com/docs/build-skills#where-to-save-skills)、[Claude Code官方目录](https://code.claude.com/docs/en/skills#choose-where-skills-load)。

## 调用示例

Codex CLI或IDE会话中用`/skills`选择，或输入：

```text
$research-to-report-and-briefing
请独立调研某项技术，面向跨方向系统专家撰写报告，并按需要准备汇报材料。
先明确已有资料、研究重点和交付阶段，保留可追踪来源。
```

Claude Code会话中使用：

```text
/research-to-report-and-briefing 请独立调研某项技术，面向跨方向系统专家撰写报告，并按需要准备汇报材料。
```

桌面端Codex可通过技能面板或`@`选择。已有项目可以指定当前成品、辅助文档与本轮修改范围，继续沿用有效记录。技能按任务加载参考文件，具体字体、时长、成果组合和领域参数保存在项目中。Claude Code适配使用技能文件与Python助手，具体成品工具由对应运行环境提供。

## 项目记忆助手

助手需要 **Python 3.9及以上版本**，仅使用标准库。报告、PPT、PDF的制作与渲染由运行环境及相应工具提供。

在技能仓库目录运行下列示例，将研究项目放在仓库外的独立目录。

Windows PowerShell：

```powershell
$ResearchProject = Join-Path $env:USERPROFILE 'research-projects\my-topic'
py -3 scripts/project_memory.py init --root "$ResearchProject" --topic "研究主题" --deliverable report --deliverable slides --memory-profile full
py -3 scripts/project_memory.py validate-config --root "$ResearchProject"
```

Linux/WSL：

```bash
research_project="$HOME/research-projects/my-topic"
python3 scripts/project_memory.py init --root "$research_project" --topic "研究主题" --deliverable report --deliverable slides --memory-profile full
python3 scripts/project_memory.py validate-config --root "$research_project"
```

`full`建立六份辅助文档；`compact`合并为三份。助手还提供配置更新、显式迁移、交付检查、文件指纹快照及验证。初始化模板需要根据实际任务填写，已有文件会保留。子命令参数用`--help`查看，完整约定见[项目记忆与配置](references/project-memory.md)。研究成品、原始资料和项目记录保存在各自项目目录中。

## 仓库结构

```text
SKILL.md                         技能入口与按任务加载规则
agents/openai.yaml               技能展示信息与默认调用提示
docs/                            两套工具在Windows/Linux上的安装与使用
references/                      研究、解释、写作、汇报、视觉与质量方法
assets/                          辅助文档模板、配置结构和可选示例
scripts/project_memory.py        项目记忆与文件身份助手
tests/test_project_memory.py     助手行为回归测试
```

视觉、偏好和时间预算资产是可覆盖的示例，采用时按项目实际情况调整。

## 测试与维护

运行回归测试：

Windows：

```powershell
py -3 -B tests/test_project_memory.py
```

Linux/WSL：

```bash
python3 -B tests/test_project_memory.py
```

修改时保持技能入口、参考方法、配置、示例和助手说明一致。脚本修改补充相应行为测试；内容方法修改使用实际段落或页面检验；涉及成品格式和版式的修改进行相应渲染检查。

版本记录与旧项目兼容说明见[版本与项目升级](references/release-history.md)。技能版本维护在 `SKILL.md` 的 `metadata.version` 和助手的 `VERSION` 中，配置结构兼容性由 `schema_version` 决定。
