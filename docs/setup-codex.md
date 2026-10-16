# Codex：Windows、Linux与WSL安装及使用

核对日期：2026-10-16。本文依据当前OpenAI官方文档，使用默认用户目录。技能自身版本见仓库`SKILL.md`；本机Codex版本用`codex --version`查看。

## 1．默认目录与运行环境

| 用途 | Windows原生 | Linux或WSL内部 |
| --- | --- | --- |
| 用户级技能根目录 | `%USERPROFILE%\.agents\skills\` | `~/.agents/skills/` |
| 本技能安装目录 | `%USERPROFILE%\.agents\skills\research-to-report-and-briefing\` | `~/.agents/skills/research-to-report-and-briefing/` |
| 用户配置文件 | `%USERPROFILE%\.codex\config.toml` | `~/.codex/config.toml` |
| 项目级技能目录 | `<项目根目录>\.agents\skills\research-to-report-and-briefing\` | `<项目根目录>/.agents/skills/research-to-report-and-briefing/` |
| 项目级配置文件 | `<项目根目录>\.codex\config.toml` | `<项目根目录>/.codex/config.toml` |

技能目录与配置目录承担不同职责。当前新安装采用`.agents/skills`；此前某些环境中存在的`.codex/skills`不作为本文的新安装默认位置。项目配置仅在信任该项目后加载。[官方技能目录](https://learn.chatgpt.com/docs/build-skills#where-to-save-skills)、[配置说明](https://learn.chatgpt.com/docs/config-file/config-basic)。

Windows原生程序使用Windows用户目录；在WSL中启动的Codex使用该Linux发行版的用户目录，例如`/home/alice/.agents/skills/`。WSL按独立Linux环境安装，当前Codex需要WSL2。以下Windows与Linux命令分别在各自终端执行。[官方WSL说明](https://learn.chatgpt.com/docs/windows/wsl)。

## 2．Windows原生安装

已有可用的Codex桌面端或IDE扩展时，可直接进行技能目录放置并在宿主中选择技能；下列CLI步骤提供终端使用方式。

### 2.1 准备终端与依赖

使用PowerShell。准备Git，以及Python 3.9或以上版本；Python用于本技能的项目记忆助手。可从[Git官方](https://git-scm.com/install/windows)和[Python官方](https://www.python.org/downloads/windows/)安装。

```powershell
git --version
py -3 --version
```

如果Python已配置为`python`命令，可将后文的`py -3`替换为`python`，先确认其版本。

### 2.2 安装Codex并登录

在新PowerShell窗口运行官方Windows安装命令：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://chatgpt.com/codex/install.ps1 | iex"
```

按安装器提示完成后，重新打开终端并检查命令：

```powershell
Get-Command codex
codex --version
```

安装器负责程序位置与PATH；`Get-Command`给出当前实际执行路径，技能文件放入第1节的用户级技能目录。[官方CLI安装说明](https://learn.chatgpt.com/docs/codex/cli)。

### 2.3 安装本技能

将`<仓库URL>`替换为本仓库发布后的真实Git地址，再执行：

```powershell
$SkillParent = Join-Path $env:USERPROFILE '.agents\skills'
$SkillRoot = Join-Path $SkillParent 'research-to-report-and-briefing'
New-Item -ItemType Directory -Path $SkillParent -Force | Out-Null
git clone '<仓库URL>' "$SkillRoot"
Test-Path -LiteralPath (Join-Path $SkillRoot 'SKILL.md')
```

最后一行应返回`True`。目标目录已有安装时，使用第7节的更新方法。

也可下载仓库ZIP，解压后把包含`SKILL.md`、`references`、`assets`、`scripts`的完整目录放到`$SkillRoot`。最终应直接存在`$SkillRoot\SKILL.md`，而不是再多套一层仓库目录。

### 2.4 创建研究项目并使用

```powershell
$ProjectRoot = Join-Path $env:USERPROFILE 'research-projects\my-topic'
New-Item -ItemType Directory -Path $ProjectRoot -Force | Out-Null
codex -C "$ProjectRoot" --search
```

首次启动按CLI提示登录。进入会话后，用`/skills`选择技能，或输入：

```text
$research-to-report-and-briefing
请围绕本目录的研究主题开展独立调研，面向跨方向系统专家撰写报告。
已有草稿仅作参考；关键机制需要原图、完整算例和可追踪来源。
请按本轮成果范围维护辅助文档，并检查实际成品。
```

`--search`用于需要当前资料的联网检索；已有冻结资料的纯文字修订可直接运行`codex -C "$ProjectRoot"`。CLI或IDE中使用`$`提及技能，桌面端可通过技能面板或`@`选择。[官方调用说明](https://learn.chatgpt.com/docs/build-skills#how-codex-uses-skills)。

## 3．Linux原生安装

### 3.1 准备依赖

Debian/Ubuntu可以运行：

```bash
sudo apt update
sudo apt install -y git curl python3
git --version
python3 --version
```

其他发行版用相应包管理器安装Git、curl及Python，确认Python至少为3.9；后续步骤相同。

### 3.2 安装Codex

```bash
curl -fsSL https://chatgpt.com/codex/install.sh | sh
```

完成安装后按安装器提示使PATH生效；新开终端检查：

```bash
command -v codex
codex --version
```

这是当前官方独立安装器路径；已使用npm等渠道安装的用户可沿原渠道维护，不需要为技能重新安装一份CLI。[官方安装渠道](https://learn.chatgpt.com/docs/codex/cli)。

### 3.3 安装技能并启动项目

```bash
mkdir -p "$HOME/.agents/skills"
git clone '<仓库URL>' "$HOME/.agents/skills/research-to-report-and-briefing"
test -f "$HOME/.agents/skills/research-to-report-and-briefing/SKILL.md"

mkdir -p "$HOME/research-projects/my-topic"
codex -C "$HOME/research-projects/my-topic" --search
```

先替换真实仓库地址。`test -f`成功时通常没有输出；可用`ls`查看该`SKILL.md`。会话内的登录、`/skills`及`$research-to-report-and-briefing`调用与Windows相同。

## 4．Windows上的WSL2

若选择在WSL运行，先在管理员PowerShell安装并进入发行版：

```powershell
wsl --install
wsl
```

完成Linux用户创建后，在WSL终端执行第3节。技能装到WSL的`~/.agents/skills/`，配置在WSL的`~/.codex/config.toml`。研究项目宜放在Linux用户目录，例如`~/research-projects/my-topic`；不要把Windows侧已经安装CLI视为WSL侧安装已完成。[官方WSL步骤](https://learn.chatgpt.com/docs/windows/wsl)。

## 5．项目记忆助手

助手从技能目录执行，项目内容写到独立研究目录。根据本轮成果选择`--deliverable`，以下示例同时请求报告与PPT，并使用六份辅助记录。

Windows PowerShell：

```powershell
$SkillRoot = Join-Path $env:USERPROFILE '.agents\skills\research-to-report-and-briefing'
$ProjectRoot = Join-Path $env:USERPROFILE 'research-projects\my-topic'
py -3 -X utf8 "$SkillRoot\scripts\project_memory.py" init --root "$ProjectRoot" --topic "研究主题" --deliverable report --deliverable slides --memory-profile full
py -3 -X utf8 "$SkillRoot\scripts\project_memory.py" validate-config --root "$ProjectRoot"
```

Linux/WSL：

```bash
skill_root="$HOME/.agents/skills/research-to-report-and-briefing"
project_root="$HOME/research-projects/my-topic"
python3 "$skill_root/scripts/project_memory.py" init --root "$project_root" --topic "研究主题" --deliverable report --deliverable slides --memory-profile full
python3 "$skill_root/scripts/project_memory.py" validate-config --root "$project_root"
```

初始化后，项目包含`.research-briefing/project.json`与`研究辅助文档/`。按实际任务填写，再开始制作。`compact`可将六类信息合为三份文件。已有项目直接读取现有记录，不必重复初始化。

`validate-config`默认检查结构；已登记交付清单并生成成品后，加入`--check-delivery`核对必交文件。快照记录的是文件身份，原文件另行保留。更多命令见[项目记忆与配置](../references/project-memory.md)。

## 6．项目级安装与必要配置

仅一个项目使用时，可把技能内容放入该项目的以下位置：

```text
my-project/
└── .agents/
    └── skills/
        └── research-to-report-and-briefing/
            ├── SKILL.md
            ├── references/
            ├── assets/
            └── scripts/
```

从仓库复制时保留完整内容，省略仓库自己的`.git`目录；这样上层项目可直接跟踪技能文件。随后从`my-project`启动Codex。用户级与项目级二选一即可；同名安装会分别出现，不会合并。[技能发现规则](https://learn.chatgpt.com/docs/build-skills#where-to-save-skills)。

默认安装通常不需要新增技能启用项。需要实时研究时可用前述`--search`；若长期采用实时检索，可在现有用户`config.toml`中设置顶层键：

```toml
web_search = "live"
```

编辑已有文件时合并该设置，保留其他配置。技能的研究重点、成果组合和时长写在研究项目记录中，模型与运行权限由Codex环境决定。[官方配置选项](https://learn.chatgpt.com/docs/config-file/config-basic)。

## 7．更新与检查

Git安装的技能可在所选安装目录更新：

```powershell
git -C "$env:USERPROFILE\.agents\skills\research-to-report-and-briefing" pull --ff-only
```

```bash
git -C "$HOME/.agents/skills/research-to-report-and-briefing" pull --ff-only
```

ZIP或复制安装按新版本重新放置内容；本地自行修改的部分先提交或另存。Codex会检测技能变化，未出现时重新启动。配置文件改动后按官方要求重启Codex。[加载与重载](https://learn.chatgpt.com/docs/build-skills)。

遇到未识别时，依次核对：

1. `SKILL.md`是否直接位于对应技能目录，是否多了一层ZIP文件夹。
2. 当前运行的是Windows原生还是WSL/Linux，是否检查了对应用户目录。
3. 是否安装了两份同名技能；按选择器中的实际路径确认要使用的一份。
4. `config.toml`中是否有针对该技能的`[[skills.config]]`且`enabled = false`。需要恢复时修改该已有项，再重启。
5. Python命令是否存在、版本是否满足助手要求。Word/PPT/PDF制作还需要宿主提供相应工具。

## 官方依据

- [Build skills](https://learn.chatgpt.com/docs/build-skills)：目录、调用、变化检测、禁用配置与元数据。
- [Codex CLI](https://learn.chatgpt.com/docs/codex/cli)：Windows/Linux当前安装器与登录。
- [Config basics](https://learn.chatgpt.com/docs/config-file/config-basic)：默认配置文件、配置层次、实时检索。
- [WSL](https://learn.chatgpt.com/docs/windows/wsl)：WSL2运行环境与安装位置。
