# 在 Codex 中安装与使用

适用于本仓库 **2.0.0**。功能、依赖和共同安装约定以 [README](../README.md) 为主；字体、路径、引擎和渲染差异见[环境适配](../references/portability.md)。

## 1. 准备源码与宿主

已有可用的 Codex 即可安装技能；宿主安装与登录请使用 [Codex 官方说明](https://learn.chatgpt.com/docs/codex/cli)。技能本身不提供宿主安装器、联网服务或 PPT 制作引擎。

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
| 当前用户 | `~/.agents/skills/research-to-report-and-briefing/` |
| 指定项目 | `<项目>/.agents/skills/research-to-report-and-briefing/` |

`~` 是运行 Codex 的用户主目录。Windows 原生与 Linux/WSL 使用各自的用户目录；自定义或旧环境按实际发现路径处理。两种范围通常选一种，避免同名副本混淆。[官方本地发现规则](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills)

### 推荐：使用随包安装助手

在上述源码目录执行；需要 Python 3.9+，助手只用标准库。

Windows PowerShell：

```powershell
py -3 scripts/setup_skill.py check --host codex
py -3 scripts/setup_skill.py install --host codex
```

Linux/WSL：

```bash
python3 scripts/setup_skill.py check --host codex
python3 scripts/setup_skill.py install --host codex
```

按实际环境可用 `python` 或解释器完整路径替换命令开头。只安装到一个已存在的研究项目时，在 `install --host codex` 后追加：

```text
--scope project --project "实际项目路径"
```

使用已确认的其他技能父目录时，使用 `install --skills-dir "实际技能父目录"`，不要同时给出 `--host`、`--scope` 或 `--project`。

助手会检查包资源，跳过仓库 `.git` 等明确排除项后复制；它不会配置 Codex 或安装外部依赖。`check` 通过仅说明本包检查通过，不代表宿主已加载、联网可用或 PPT 已能制作和渲染。

### 手动复制

无需 Python 也能手动安装：将干净源码的完整技能目录复制到所选位置，省略 `.git`，保留配套资源。最终必须直接存在 `skills/research-to-report-and-briefing/SKILL.md`。目标已有内容时，先按下一节处理。

## 3. 升级并保留已有安装

1. 先确认当前加载路径，并保留已有安装及个人修改。若旧目录是 Git 仓库，也保留其历史和未提交改动。
2. 将旧目录移至技能发现范围之外作为备份，使原安装目标不存在；不要仅复制备份后把旧目录留在目标位置。
3. 从准备好的干净新源码运行安装助手，或复制完整新目录。助手遇到内容不同的已有目标会拒绝覆盖；相同内容则不重复写入。
4. 在 Codex 中确认新路径与版本。更新未出现时，重新启动会话。[官方更新发现说明](https://learn.chatgpt.com/docs/build-skills)

版本号相同也可能有内容修订，应同时核对源文件或提交记录。原有项目资料与 `.research-briefing` 项目记录留在研究目录中，无需随技能升级重建。

## 4. 在研究项目中调用

在独立的研究项目目录打开 Codex，在**对话输入框**选择技能或输入：

```text
$research-to-report-and-briefing
根据本目录材料制作面向技术评审的PPT。必要时补充调研，说明关键机制、
证据与方案取舍，使用完整图表和可直接照读的逐页备注。总时长约20分钟。
```

这是对话示例，不是终端命令。也可明确要求“使用 research-to-report-and-briefing 完成……”；确认选择器中的技能路径，避免调用旧副本。[官方技能调用说明](https://learn.chatgpt.com/docs/build-skills)

首次制作前，让代理核对可用搜索工具、PPT 引擎、字体与最终文件渲染方式。`agents/openai.yaml` 是可选界面信息；不需要把技能正文复制进 `AGENTS.md`。

## 5. 常见问题

- **找不到技能**：核对目录层级、当前用户/WSL环境、所选作用域及同名副本，再刷新或重启。
- **助手提示目录名不匹配**：去掉 ZIP 解压目录后缀，使用本技能的标准名称。
- **目标内容不同**：先保留并移开旧目录，再安装；不要用覆盖操作绕过保护。
- **技能能加载但无法制作PPT**：检查实际制作引擎与其依赖，详见 [README](../README.md#依赖与能力边界)。

本页官方目录与调用规则核对于 2026-10-21。文档核对不代表所有 Codex 版本、Windows/Linux 或渲染组合均已实测。
