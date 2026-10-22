# 在 Claude Code 中安装与使用

适用于本仓库 **3.1.0**。功能、依赖和共同安装约定以 [README](../README.md) 为主；字体、路径、引擎和渲染差异见[环境适配](../references/portability.md)。

## 1. 准备源码与宿主

已有可用的 Claude Code 即可安装技能；宿主安装、登录与运行要求请使用 [Claude Code 官方说明](https://code.claude.com/docs/en/setup)。本技能不安装 Claude Code，也不修改账户或宿主权限配置。

在存放源码的位置取得本仓库：

```text
git clone https://github.com/amunlau/research-to-report-and-briefing.git research-to-report-and-briefing
cd research-to-report-and-briefing
```

也可从[仓库页面](https://github.com/amunlau/research-to-report-and-briefing)下载 ZIP。将直接包含 `SKILL.md` 的解压目录改名为 `research-to-report-and-briefing`，去掉 `-main` 等后缀，再进入该目录。使用前查看 `SKILL.md` 的 `metadata.version`，确认拿到所需版本。

研究项目、生成文件和虚拟环境均放在源码仓库之外。安装前使用干净源码，避免夹带个人配置、凭据、缓存或临时资料；Git 的忽略规则不代表所有被忽略文件都会自动从安装中排除。

## 2. 选择安装位置

| 范围 | 技能目录 |
| --- | --- |
| 当前用户 | `~/.claude/skills/research-to-report-and-briefing/` |
| 指定项目 | `<项目>/.claude/skills/research-to-report-and-briefing/` |

`~` 是运行 Claude Code 的用户主目录。Windows 原生与 Linux/WSL 使用各自的用户目录；自定义环境按实际发现位置处理。本页适用于本地技能安装，不会自动让远程或云端会话获得同一份文件。[官方技能位置与范围](https://code.claude.com/docs/en/skills#choose-where-skills-load)

### 推荐：使用随包安装助手

在上述源码目录执行；需要 Python 3.9+，助手只用标准库。

Windows PowerShell：

```powershell
py -3 scripts/setup_skill.py check --host claude
py -3 scripts/setup_skill.py install --host claude
```

Linux/WSL：

```bash
python3 scripts/setup_skill.py check --host claude
python3 scripts/setup_skill.py install --host claude
```

按实际环境可用 `python` 或解释器完整路径替换命令开头。只安装到一个已存在的研究项目时，在 `install --host claude` 后追加：

```text
--scope project --project "实际项目路径"
```

助手的 `--host claude` 使用表中的默认目录。若宿主采用其他配置根或技能目录，先确认实际技能父目录，再使用 `install --skills-dir "实际技能父目录"`；不要同时给出 `--host`、`--scope` 或 `--project`。

助手会检查包资源，跳过仓库 `.git` 等明确排除项后复制；它不会安装 PPT 引擎或调整 Claude Code 的工具权限。`check` 通过仅说明本包检查通过，不代表宿主已加载、联网可用或最终 PPT 可渲染。

### 手动复制

无需 Python 也能手动安装：将干净源码的完整技能目录复制到所选位置，省略 `.git`，保留配套资源。最终必须直接存在 `skills/research-to-report-and-briefing/SKILL.md`。目标已有内容时，先按下一节处理。

## 3. 升级并保留已有安装

1. 先确认当前加载路径，并保留已有安装及个人修改。若旧目录是 Git 仓库，也保留其历史和未提交改动。
2. 将旧目录移至技能发现范围之外作为备份，使原安装目标不存在；不要仅复制备份后把旧目录留在目标位置。
3. 从准备好的干净新源码运行安装助手，或复制完整新目录。助手遇到内容不同的已有目标会拒绝覆盖；相同内容则不重复写入。
4. 回到 Claude Code，使用 `/reload-skills` 或重新启动会话，再确认当前技能。完整包升级后建议开启新会话，避免已加载的旧内容干扰。[官方重载说明](https://code.claude.com/docs/en/skills#edit-a-skill-during-a-session)

版本号相同也可能有内容修订，应同时核对源文件或提交记录。原有项目资料与 `.research-briefing` 项目记录留在研究目录中，无需随技能升级重建。

## 4. 在研究项目中调用

在独立的研究项目目录打开 Claude Code，在**对话输入框**输入：

```text
/research-to-report-and-briefing
从零调研指定技术方向，核对原始来源后制作PPT，附可直接照读的逐页备注。
听众为有相关基础的工程师，重点比较机制、性能条件和限制，总时长约20分钟。
```

这是对话示例，不是终端命令。技能也可按描述被自动采用；明确调用便于确认使用哪份流程。默认只保留一个合适作用域下的同名安装，避免优先级导致调用旧副本。[官方调用与同名技能规则](https://code.claude.com/docs/en/skills)

首次制作前，让代理核对可用搜索工具、PPT 引擎、字体与最终文件渲染方式。`agents/openai.yaml` 为 Codex 的可选界面信息，Claude Code 的共同流程不依赖它；不需要把技能正文复制进 `CLAUDE.md`。

## 5. 常见问题

- **命令未出现**：核对目录层级、当前用户/WSL环境、实际技能父目录及同名副本，再重载或重启。
- **助手提示目录名不匹配**：去掉 ZIP 解压目录后缀，使用本技能的标准名称。
- **目标内容不同**：先保留并移开旧目录，再安装；不要用覆盖操作绕过保护。
- **能调用但没有所需工具**：技能不会自动赋予联网或软件能力，依赖要求见 [README](../README.md#依赖与能力边界)。

本页官方目录与调用规则核对于 2026-10-21。文档核对不代表 Claude Code 已实际加载本包，也不代表所有 Windows/Linux 或渲染组合均已实测。
