# Claude Code：Windows 与 Linux 安装、配置和使用

本文适用于本地终端中的 Claude Code。安装命令、默认路径和技能行为已于 **2026-10-16** 检索并实际打开 Claude 官方文档核对；后续版本以所链接的官方页面为准。

本技能通过 `SKILL.md` 加载研究方法、参考文件和模板，并通过本机 Python 运行项目记忆助手。报告、PPT、PDF 制作与渲染使用当前 Claude Code 环境实际具备的工具；仓库中的 `agents/openai.yaml` 属于 Codex 展示配置，Codex 专用工具需另行适配。

## 1. 先选择运行环境

- **Windows 原生**：在 PowerShell 中安装和启动，适合 Windows 路径、字体、Office 和本机工具。
- **Linux 原生**：在 Linux 终端中安装和启动。
- **Windows 上的 WSL**：按本文 Linux 步骤在 WSL 终端内安装、登录并放置技能；其中的 `~` 指 Linux 用户主目录。

当前官方文档明确：**Windows 原生安装中的 Git for Windows 为可选项**。安装后 Claude Code 可使用 Git Bash，未安装时使用 PowerShell 工具。本文用户级安装采用 `git clone`，这一步需要 Git，也可改用 ZIP 完整副本。参见[官方 Windows 安装说明](https://code.claude.com/docs/en/setup#set-up-on-windows)。

## 2. 安装并检查 Claude Code CLI

### Windows 原生：PowerShell

打开普通 PowerShell 窗口，执行官方推荐的原生安装命令：

```powershell
irm https://claude.ai/install.ps1 | iex
```

完成后打开**新的** PowerShell 窗口：

```powershell
claude --version
claude doctor
```

原生启动程序默认位于：

```text
%USERPROFILE%\.local\bin\claude.exe
```

需要检查命令来自哪里时：

```powershell
Get-Command claude -All
Test-Path -LiteralPath "$env:USERPROFILE\.local\bin\claude.exe"
```

如果文件存在但新窗口仍找不到 `claude`，按[官方 PATH 排查步骤](https://code.claude.com/docs/en/troubleshoot-install#verify-your-path)将 `%USERPROFILE%\.local\bin` 加入用户 PATH，并重新打开终端；编辑器内置终端还可能需要重启编辑器。

### Linux 原生：Bash

在 Linux 终端执行：

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

完成后打开新终端，检查：

```bash
claude --version
claude doctor
command -v claude
```

原生启动程序默认为 `~/.local/bin/claude`，Linux 原生安装器维护的版本默认在 `~/.local/share/claude/versions/`。若找不到命令，可先直接检查：

```bash
ls -l "$HOME/.local/bin/claude"
"$HOME/.local/bin/claude" --version
```

文件存在而 `command -v claude` 无输出时，按[官方 PATH 排查步骤](https://code.claude.com/docs/en/troubleshoot-install#verify-your-path)把 `~/.local/bin` 加到当前 shell 的 PATH。Alpine 等 musl 发行版还需按[官方附加依赖说明](https://code.claude.com/docs/en/setup#alpine-linux-and-musl-based-distributions)准备其依赖。

以上是[官方推荐的 Native Install](https://code.claude.com/docs/en/setup#install-claude-code)及其默认路径。npm、WinGet 和 Linux 包管理器安装各有自己的位置；`~/.claude/local/` 属于旧版安装路径。已有安装先用 `claude --version`、`claude doctor` 确认状态。

### 首次登录与启动目录

在研究项目目录运行 `claude`，按浏览器提示完成登录。账户或组织提供商的要求见[官方快速开始](https://code.claude.com/docs/en/quickstart)与[认证说明](https://code.claude.com/docs/en/authentication)。

Windows：

```powershell
$projectDir = Join-Path $env:USERPROFILE 'Documents\my-research'
New-Item -ItemType Directory -Path $projectDir -Force | Out-Null
Set-Location -LiteralPath $projectDir
claude
```

Linux：

```bash
project_dir="$HOME/work/my-research"
mkdir -p "$project_dir"
cd "$project_dir"
claude
```

上面的研究目录只是示例，可替换为实际项目目录。

## 3. 配置与技能的默认目录

以下路径均指**未自定义配置目录时**的默认值。

Windows 原生：

```text
%USERPROFILE%\.claude\settings.json                      用户设置
%USERPROFILE%\.claude.json                               Claude Code 自行维护的全局状态
%USERPROFILE%\.claude\skills\research-to-report-and-briefing\SKILL.md
                                                         用户级技能入口
<研究项目>\.claude\settings.json                         项目共享设置
<研究项目>\.claude\settings.local.json                   项目个人设置
<研究项目>\.claude\skills\research-to-report-and-briefing\SKILL.md
                                                         项目级技能入口
```

Linux 原生或 WSL：

```text
~/.claude/settings.json                                 用户设置
~/.claude.json                                          Claude Code 自行维护的全局状态
~/.claude/skills/research-to-report-and-briefing/SKILL.md  用户级技能入口
<研究项目>/.claude/settings.json                         项目共享设置
<研究项目>/.claude/settings.local.json                   项目个人设置
<研究项目>/.claude/skills/research-to-report-and-briefing/SKILL.md
                                                        项目级技能入口
```

用户级技能用于本机多个项目；项目级技能用于对应项目及团队共享。`<研究项目>` 指放置资料、项目记录和成品的工作目录。

默认技能位置依据[官方技能位置说明](https://code.claude.com/docs/en/skills#choose-where-skills-load)；Windows 的 `~/.claude` 展开规则及设置文件依据[官方设置说明](https://code.claude.com/docs/en/settings#settings-files-and-who-they-affect)。若已设置 `CLAUDE_CONFIG_DIR`，按[官方目录参考](https://code.claude.com/docs/en/claude-directory)将下面用户级示例中的 `.claude` 根目录换为该变量指定的目录。

## 4. 放置技能：选择用户级或项目级

用户级安装可直接克隆；项目级安装采用排除 `.git` 的完整文件副本，便于随研究项目共同管理。以下 **`<仓库URL>` 请替换为本仓库实际发布的 Git 地址**。命令用于目标尚不存在的首次安装，已有副本请看第 8 节。

### Windows：用户级

```powershell
$repoUrl = '<仓库URL>'
$skillsRoot = Join-Path $env:USERPROFILE '.claude\skills'
$skillDir = Join-Path $skillsRoot 'research-to-report-and-briefing'
if (Test-Path -LiteralPath $skillDir) { throw '目标已存在，请检查或按更新步骤处理。' }
New-Item -ItemType Directory -Path $skillsRoot -Force | Out-Null
git clone $repoUrl $skillDir
Test-Path -LiteralPath (Join-Path $skillDir 'SKILL.md')
```

最后应输出 `True`。如果已经设置 `CLAUDE_CONFIG_DIR`，将 `$skillsRoot` 改为 `Join-Path $env:CLAUDE_CONFIG_DIR 'skills'`。

### Linux：用户级

```bash
repo_url='<仓库URL>'
skills_root="$HOME/.claude/skills"
skill_dir="$skills_root/research-to-report-and-briefing"
if [ -e "$skill_dir" ]; then
  printf '%s\n' '目标已存在，请检查或按更新步骤处理。'
else
  mkdir -p "$skills_root"
  git clone "$repo_url" "$skill_dir"
  test -f "$skill_dir/SKILL.md" && printf '%s\n' '技能入口存在'
fi
```

如果已经设置 `CLAUDE_CONFIG_DIR`，将 `skills_root` 改为 `"$CLAUDE_CONFIG_DIR/skills"`。

### Windows / Linux：项目级完整副本

1. 下载并解压本仓库 ZIP，或准备已有完整副本，定位直接含 `SKILL.md` 的仓库根目录。
2. 在实际研究项目中创建 `.claude/skills/research-to-report-and-briefing/`。
3. 将源根目录的全部文件和文件夹复制进去，**排除源仓库自己的 `.git` 目录或文件**，保留 `references/`、`assets/`、`scripts/` 等配套内容。已有目标先按第 8 节处理本地改动。
4. 检查最终层级如下，再从研究项目目录启动 Claude Code。

```text
<研究项目>/
└── .claude/
    └── skills/
        └── research-to-report-and-briefing/
            ├── SKILL.md
            ├── README.md
            ├── references/
            ├── assets/
            ├── scripts/
            ├── agents/
            ├── tests/
            └── ...其他仓库文件（不含 .git）
```

Windows 在研究项目的 PowerShell 中验证，结果应为 `True`：

```powershell
$skillDir = Join-Path (Get-Location).Path '.claude\skills\research-to-report-and-briefing'
Test-Path -LiteralPath (Join-Path $skillDir 'SKILL.md')
Get-ChildItem -LiteralPath $skillDir -Force
```

Linux 在研究项目的终端中验证：

```bash
skill_dir="$PWD/.claude/skills/research-to-report-and-briefing"
test -f "$skill_dir/SKILL.md" && printf '%s\n' '技能入口存在'
ls -a "$skill_dir"
```

文件副本可直接纳入研究项目的版本管理。团队已有 Git submodule 管理规范时，也可按该规范分发。用户级安装同样可以采用上述完整复制方式，将目标换为第 3 节的用户技能目录；已有 Codex 副本可作为复制来源。

## 5. 最小配置与可选 Git Bash

放到技能目录后即可检查发现情况。可在 Claude Code 会话中用 `/config` 调整个人选项，用 `/status` 查看实际加载的设置来源；用户设置文件按需创建，见[官方设置文件创建说明](https://code.claude.com/docs/en/settings#find-or-create-your-settings-files)。

如果 Windows 已安装 Git for Windows，但 Claude Code 找不到 Git Bash，可按官方说明将以下片段**合并**到用户 `settings.json` 的现有内容中；路径应替换为本机实际的 `bash.exe`：

```json
{
  "env": {
    "CLAUDE_CODE_GIT_BASH_PATH": "C:\\Program Files\\Git\\bin\\bash.exe"
  }
}
```

将该定位选项与现有设置合并，保持严格 JSON 格式。来源：[官方 Windows 原生安装说明](https://code.claude.com/docs/en/setup#install-on-native-windows)。

## 6. 发现、调用与修改后重载

在研究项目中启动 `claude` 后，在 **Claude Code 输入框**输入：

```text
/skills
```

确认列表出现 `research-to-report-and-briefing`，再显式调用：

```text
/research-to-report-and-briefing 请调研某项技术，面向跨方向系统专家形成中文研究报告。先读取当前项目资料与已有记录，核对关键事实的原始来源，并按本轮需要制作汇报材料。
```

也可以自然描述匹配的研究任务，由 Claude Code 按技能描述选择。示例任务说明可换为报告转汇报、局部修订或仅做样稿等实际需求。

按[官方修改与重载说明](https://code.claude.com/docs/en/skills#edit-a-skill-during-a-session)，当前版本在普通本地会话中监视已有技能目录，新增、编辑或删除 `SKILL.md` 可在会话内被发现；如果会话启动时顶层技能目录尚不存在，创建后运行：

```text
/reload-skills
/skills
```

这类新目录在本次会话中仍未被监视，后续修改后也要再次 `/reload-skills`。自动变化检测仅涵盖 `SKILL.md` 文本；修改 `references/` 后让 Claude 重新读取相应文件，Python 脚本在下次执行时读取磁盘代码。

已经载入对话的技能正文会保留在上下文中，删除技能目录不会抹去已载入内容。更新后可重新调用；要从干净上下文验证新版本，退出并新开会话，再确认 `/skills` 和实际任务行为。旧版没有 `/reload-skills` 时，也可新开会话检查。来源：[官方技能内容生命周期](https://code.claude.com/docs/en/skills#skill-content-lifecycle)。

## 7. 使用 Python 项目记忆助手

助手需要 **Python 3.9+**，只依赖标准库。Windows 示例使用 Python launcher 的 `py -3`；本机使用 `python` 命令时可相应替换，并先确认版本。

### Windows PowerShell

用户级安装示例；项目级安装请把 `$skillDir` 改为对应项目 `.claude\skills\research-to-report-and-briefing` 的绝对路径：

```powershell
py -3 --version
$skillDir = Join-Path $env:USERPROFILE '.claude\skills\research-to-report-and-briefing'
$helper = Join-Path $skillDir 'scripts\project_memory.py'
$projectDir = Join-Path $env:USERPROFILE 'Documents\my-research'

py -3 $helper --help
py -3 $helper init --root $projectDir --topic '研究主题' --deliverable report --deliverable slides --memory-profile full
py -3 $helper validate-config --root $projectDir
```

### Linux Bash

```bash
python3 --version
skill_dir="$HOME/.claude/skills/research-to-report-and-briefing"
helper="$skill_dir/scripts/project_memory.py"
project_dir="$HOME/work/my-research"

python3 "$helper" --help
python3 "$helper" init --root "$project_dir" --topic '研究主题' --deliverable report --deliverable slides --memory-profile full
python3 "$helper" validate-config --root "$project_dir"
```

`--root` 指向研究项目；使用 `CLAUDE_CONFIG_DIR` 或项目级安装时，同步调整助手所在路径。

初始化会在项目中建立 `.research-briefing/project.json` 和 `研究辅助文档/`；`full` 使用六类记录，`compact` 合并为三份。模板按实际任务填写，`init` 保留已有文件。后续会话让 Claude Code 读取并继续维护这些配置和记录。

需要增加演讲稿等成果时：

Windows：

```powershell
py -3 $helper update --root $projectDir --add-deliverable speaker-script
py -3 $helper validate-config --root $projectDir
```

Linux：

```bash
python3 "$helper" update --root "$project_dir" --add-deliverable speaker-script
python3 "$helper" validate-config --root "$project_dir"
```

已完成并在配置中登记实际交付文件后，可以保存和核验交付指纹：

Windows：

```powershell
py -3 $helper snapshot --root $projectDir --label review-01 --expected
py -3 $helper verify --root $projectDir --manifest '.research-briefing/snapshots/review-01.json'
```

Linux：

```bash
python3 "$helper" snapshot --root "$project_dir" --label review-01 --expected
python3 "$helper" verify --root "$project_dir" --manifest '.research-briefing/snapshots/review-01.json'
```

快照是文件指纹清单，不是成品备份，也不验证研究结论和页面质量。`--expected` 根据配置绑定交付范围，适用于已正确填写交付清单并准备好相应文件之后；每次快照使用新的标签。完整参数以脚本 `--help` 及各子命令 `--help` 为准，进一步说明见[项目记忆与配置](../references/project-memory.md)。

## 8. 更新、停用和移除

### 更新技能文件

如果目标目录由 `git clone` 得到，先检查本地改动，再进行只允许快进的更新。

Windows 用户级示例：

```powershell
$skillDir = Join-Path $env:USERPROFILE '.claude\skills\research-to-report-and-briefing'
git -C $skillDir status --short
git -C $skillDir pull --ff-only
```

Linux 用户级示例：

```bash
skill_dir="$HOME/.claude/skills/research-to-report-and-briefing"
git -C "$skill_dir" status --short
git -C "$skill_dir" pull --ff-only
```

有本地修改时先保留或整合修改。ZIP/普通副本安装先保留自定义改动，再用新版完整内容替换并继续排除源仓库的 `.git`。更新后按第 6 节重载并重新调用；已初始化的研究项目依[版本与项目升级](../references/release-history.md)决定是否显式升级。

Claude Code 程序自身的更新与技能仓库更新不同。原生安装默认自动更新；需要立即检查时，在终端运行 `claude update`，更新后重新启动会话。其他安装方式使用其相应包管理器。来源：[官方更新说明](https://code.claude.com/docs/en/setup#update-claude-code)。

### 移除本地技能

按[官方移除说明](https://code.claude.com/docs/en/skills#remove-a-skill)，删除对应的单个技能目录即可。需要保留自定义内容时，先将该目录复制到技能扫描范围之外，再删除：

- Windows 用户级：`%USERPROFILE%\.claude\skills\research-to-report-and-briefing\`。
- Linux 用户级：`~/.claude/skills/research-to-report-and-briefing/`。
- 项目级：实际项目中的 `.claude/skills/research-to-report-and-briefing/`。

移除后用 `/skills` 检查；若该目录未被本次会话监视，运行 `/reload-skills` 或新开会话。已经加载进对话的内容按第 6 节所述处理。研究项目的 `.research-briefing/`、辅助文档和成品独立保存在项目中，移除技能无需删除这些文件。

## 9. 常见问题定位

- **找不到 `claude`**：按第 2 节检查程序路径、PATH 和实际安装来源。
- **`/skills` 没有技能**：检查 `SKILL.md` 的准确层级、当前运行的是 Windows 原生还是 WSL，以及是否启用了 `CLAUDE_CONFIG_DIR`。新建顶层目录后按第 6 节重载。
- **能列出技能但助手不能运行**：检查 Python 版本、实际解释器命令、助手路径和 `--root`。Windows 中带空格的路径应作为带引号的字符串或变量传递。
- **成品生成或渲染失败**：检查本机文件制作、Office、PDF、字体和渲染工具是否满足对应格式的要求。

## 官方核对来源

以下页面均在 **2026-10-16** 实际打开核对：

- [Advanced setup](https://code.claude.com/docs/en/setup)：推荐原生安装、Windows 的 Git Bash/PowerShell/WSL 角色、Linux 安装、更新。
- [Troubleshoot installation and login](https://code.claude.com/docs/en/troubleshoot-install)：当前默认启动路径、PATH 和多安装来源排查。
- [Quickstart](https://code.claude.com/docs/en/quickstart)：项目目录启动与首次登录。
- [Authentication](https://code.claude.com/docs/en/authentication)：首次浏览器登录与账户/提供商入口。
- [Extend Claude with skills](https://code.claude.com/docs/en/skills)：用户/项目技能目录、调用、监视与重载、正文生命周期、移除。
- [Settings files and precedence](https://code.claude.com/docs/en/settings)：用户/项目设置、`~/.claude.json` 与配置目录。
- [Explore the .claude directory](https://code.claude.com/docs/en/claude-directory)：Windows 主目录展开、`CLAUDE_CONFIG_DIR` 对用户目录路径的影响。
