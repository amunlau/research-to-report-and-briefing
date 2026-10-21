# research-to-report-and-briefing

面向技术、产品与产业研究的 Agent Skill，贯通独立调研、研究报告、汇报 PPT、逐页演讲稿和作者技术解析，适用于 Codex、Claude Code 等支持 Agent Skills 的宿主。

当前源码版本：**3.0.0**。本版本承接 [amunlau/research-to-report-and-briefing](https://github.com/amunlau/research-to-report-and-briefing) 的研究与项目记忆体系，以及 2.0.0 的高质量 PPT、完整讲述备注和跨平台安装能力，进一步检查调研到成品的闭环、修订与验收一致性，并加强自然专业文字。版本变化见 [CHANGELOG](CHANGELOG.md)。

## 能完成什么

根据任务选择研究报告、可编辑 PPTX、汇报文稿、作者技术详解及必要的项目记忆；只制作用户请求的成果。仅需 PPT 时，可以先组织内容母稿，无需额外生成整篇报告。

支持三种研究起点：

| 输入方式 | 工作方式 |
| --- | --- |
| 只有主题 | 建立研究问题，检索并阅读原始来源，形成证据和论证 |
| 已有材料 | 读取文档、报告和参考稿，区分材料保真与事实核查，再组织成果 |
| 混合资料 | 沿已有内容定位关键缺口，补充影响结论和页面的证据 |

可用于市场趋势调研、技术细节解析、产品与产业比较、工作汇报及成套材料修订。既有资料范围、保密要求和联网限制优先于默认研究流程。

### 调研、成稿与持续修订

以研究问题组织来源、事实与论证，定稿时回收哪些问题已回答、有限回答或仍未解决；摘要保留影响结论的条件。仅交付报告时，不要求PPT页面计划、演讲备注或时间账。转换为最终文件后，核对章节、数字、图表、引用及限制条件是否保留。

项目记忆保存当前成果、证据入口、缺口、变更影响和下一步，支持中断恢复与增量修订；小任务可用简短记录。工作快照可以保存未完成状态，验收记录只对应实际完成的检查与文件身份。来源、内容或成品变化后，应重做受影响的检查。结构助手辅助发现缺项，论证与表达仍须结合实际内容审阅。

### PPT 与文字的默认要求

- 全稿有清晰逻辑链；标题可以概括内容、提出具体问题或表达有证据的观点，不强制每页结论化。
- 页面保留必要解释、因果条件和图表读序，支持讲者顺着页面讲述，也支持听众会后阅读。
- 常规内容页充分利用正文区域，主动采用标题签、浅底色、边框、编号和项目符号组织文字；按真实关系选择SmartArt式列表、流程、层次或矩阵，文字与必要解释保持完整。
- 分别检查整页均衡与模块内部排版；内容偏少时调整分栏、尺度和整组位置。专业原图检查有效显示区域，通过标注、编号或邻近说明建立图文对应。
- 检查文本框有效宽度和实际换行，处理不必要的提前折行、零碎短行和难读拆分；保留合理多行，在最终PPTX中核对，不靠缩字强凑一行。
- 强烈建议在统一风格下形成适度的版式多样性，结合图形比例、文字容量和讲述重点选择构图，审视连续及邻近页面的重复；连续推导与直接比较可保留稳定布局，不设版式数量或重复率配额。
- 按内容选择专业原图、数据图、密集表格和架构图；文字、表格和适合的数据图优先采用原生可编辑对象。
- 常规标题和正文默认微软雅黑，采用浅底、深正文、蓝色系基础，允许协调的辅助色；多文本块按关系选用浅底面板、色带、编号、项目符号或SmartArt式结构，保留完整解释和可读性。用户、品牌和既有模板要求可以覆盖，具体方法见[视觉表达](references/visual-expression.md)。
- 默认每页写入可直接照读的自然口语备注，并对应最终页面。普通内容页约 30—90 秒是灵活参考，复杂度及全场时长决定展开程度；用户可关闭备注。
- 文字强调具体对象、机制、依据和条件，减少空泛导语、夸饰、机械对仗及重复总结；不通过删掉必要细节来“去 AI 味”。
- 报告正文默认正常字重，标题使用实际层级样式，避免装饰性「」/『』与不必要的重复加粗；保留原文引述等合理例外，PPT保留帮助理解和扫读的选择性重点。

页数、字数和图片数量没有固定配额。页面密度服从内容、观看环境和阅读用途，最终效果需要结合实际文件检查。

## 获取源码

有 Git 时，在准备存放源码的位置执行：

```bash
git clone https://github.com/amunlau/research-to-report-and-briefing.git
cd research-to-report-and-briefing
```

也可在仓库页面选择 **Code → Download ZIP**，解压后找到直接包含 `SKILL.md` 的目录。GitHub 源码包可能使用 `research-to-report-and-briefing-main` 等目录名；无论手动复制还是使用安装助手，都先将这一层改名为 `research-to-report-and-briefing`，不要多套一层同名文件夹。

克隆或下载得到对应分支当时的内容；以其中 `SKILL.md` 的版本及 Git 提交为准，不能仅凭下载文件名判断版本。

## 安装

根目录的本节是安装说明的维护位置。按宿主查看简明入口：[Codex](docs/setup-codex.md)、[Claude Code](docs/setup-claude-code.md)。

### 方式一：复制目录

从干净源码复制完整技能目录，省略 `.git` 和缓存，保留全部配套资源；不要只复制 `SKILL.md`。选择一个适用位置：

| 使用范围 | Codex | Claude Code |
| --- | --- | --- |
| 当前用户 | `~/.agents/skills/research-to-report-and-briefing/` | `~/.claude/skills/research-to-report-and-briefing/` |
| 仅指定项目 | `<项目>/.agents/skills/research-to-report-and-briefing/` | `<项目>/.claude/skills/research-to-report-and-briefing/` |

`~` 表示运行宿主的用户主目录。Windows、Linux 和 WSL 分别使用其宿主能读取的位置；自定义安装、旧版本或受组织管理的环境以实际发现路径为准。最终结构应为 `skills/research-to-report-and-briefing/SKILL.md`。

同一个宿主通常只需选择一个作用域，避免同名副本混淆；两种宿主可以分别安装同一份源码。手动复制不要求额外安装 Python。

### 方式二：使用安装助手

已有 Python 3.9+ 时，进入包含 `SKILL.md` 的源码目录，选择实际需要的宿主执行。

Windows PowerShell：

```powershell
py -3 scripts/setup_skill.py check
py -3 scripts/setup_skill.py install --host codex
# 安装给 Claude Code 时，将 codex 改为 claude。
```

Linux shell：

```bash
python3 scripts/setup_skill.py check
python3 scripts/setup_skill.py install --host codex
# 安装给 Claude Code 时，将 codex 改为 claude。
```

若实际命令是 `python` 或解释器绝对路径，用它替换命令开头。安装到已存在的指定项目时追加 `--scope project --project "实际项目路径"`；源码目录与安装目标不能互相包含。

使用已确认的其他技能父目录时，改用 `install --skills-dir "实际技能父目录"`，不要同时提供 `--host/--scope/--project`。助手在父目录下创建同名技能目录；检查和安装前，源码目录名称须为 `research-to-report-and-briefing`，与 `SKILL.md` 中的名称一致。

助手检查必需资源和内部文档引用，不下载依赖、不修改宿主配置，也不安装 PPT 引擎。相同内容重复安装不改写；已有目标内容不同时拒绝覆盖。`check` 的环境概况只是候选发现，不能证明宿主已经加载或 PPT 可以渲染。

请从干净源码安装。研究项目、虚拟环境、生成成果及凭据放在仓库外；`.gitignore` 只控制 Git 跟踪，不决定安装助手的复制范围。

### 确认加载与升级

安装后在宿主的技能列表中确认实际路径；未出现时刷新或重新启动会话。Claude Code 可使用 `/reload-skills`；Codex 可检查技能选择器，必要时重启。本地安装不会自动同步到云端会话或另一台机器。

更新已安装副本时，先将旧目录移到技能搜索范围之外备份，使原目标目录不存在，再安装新源码。即使版本号相同，也按文件内容识别差异；不要把“下载了新源码”当作“宿主已加载新副本”。

从 1.x 或 2.x 继续已有研究项目时，保留原稿、稳定 ID、台账与快照。项目配置继续使用 `research-briefing/2`，旧 `skill_version` 记录配置来源，无需批量改号。按当前任务补充所需记录，详情见[项目升级说明](references/release-history.md)。

## 开始使用

以下内容输入宿主的**对话框**，不是终端命令。主题、材料位置和交付目标通常足够开始；已有受众、时长、模板和来源限制会被沿用。

Codex 示例：

```text
$research-to-report-and-briefing
根据工作目录中的材料，制作一份面向技术评审的 PPT。
说明关键机制、证据和方案取舍，保留专业图表及完整演讲备注。
```

Claude Code 示例：

```text
/research-to-report-and-briefing
从零调研指定技术方向，核对原始来源后制作 PPT，附逐页演讲备注。
受众为有相关基础的工程师，重点比较机制、性能条件和限制。
```

也可直接说“请使用 research-to-report-and-briefing 完成……”。自动匹配由宿主决定；明确调用便于确认使用的是哪份技能。

## 依赖与能力边界

| 工作 | 必要能力 |
| --- | --- |
| 读取技能、组织研究与写作 | 支持技能的宿主及资料读取能力 |
| 运行本包四个助手 | Python 3.9+，仅标准库 |
| 从零联网调研 | 宿主可用的检索和来源阅读工具 |
| 制作 PPTX | 可用制作引擎；优先已安装的 `ppt-master` 及其依赖，也可采用满足任务要求的替代能力 |
| 核对最终版面 | 能处理最终 PPTX 的渲染器、实际字体及查看能力 |

本仓库提供流程、参考说明、内容契约和检查助手，没有内置 PPT Master、Office、LibreOffice、字体或搜索服务，也无需安装方法调研中提到的全部 skills。制作前应发现实际引擎和版本，按其真实接口执行。

缺少微软雅黑时，按项目约定选择实际可用的中文字体并记录，随后重新检查版面；严格指定字体或模板时不能静默替换。原生编辑性、完整备注及证据要求不会因换平台而自动降低。

Windows 与 Linux 共用源文件；跨平台设计不等于所有系统与宿主组合均已实测，不同渲染器也可能产生差异。结构扫描不能证明事实正确、真实版面通过或演讲效果良好。已完成与未完成的验证分别列在[验证范围](docs/validation.md)。

## 目录导航

| 位置 | 内容 |
| --- | --- |
| [SKILL.md](SKILL.md) | 共享入口与按阶段加载流程 |
| [references/](references/) | 研究、写作、图表、PPT 制作、项目记忆与适配说明 |
| [assets/](assets/) | JSON 契约、视觉配置、时间账及验收示例 |
| [scripts/](scripts/) | 安装、项目记忆、内容审查和 PPTX 提取助手 |
| [agents/openai.yaml](agents/openai.yaml) | 可选的 Codex 界面信息，核心流程不依赖它 |
| [docs/](docs/) | 宿主安装入口与验证范围 |
| [tests/](tests/) | 随仓库提供的回归检查；具体覆盖范围见验证说明 |

进一步阅读：[PPT 制作](references/ppt-production.md)、[环境适配](references/portability.md)、[写作与编辑](references/writing-and-editing.md)、[贡献与维护](CONTRIBUTING.md)。

## 维护与检查

在包含 `SKILL.md` 的源码目录执行以下命令；将 `python` 换成实际的 Python 3.9+ 命令，例如 Windows 的 `py -3` 或 Linux 的 `python3`。

```text
python -B scripts/setup_skill.py check
python -B -m unittest discover -s tests -p "test_*.py"
git diff --check
git diff --cached --check
```

回归使用本地隔离夹具，无需安装PPT制作引擎；实际覆盖范围和未验证部分见[验证说明](docs/validation.md)，贡献约定见[CONTRIBUTING](CONTRIBUTING.md)。测试通过不能代替研究内容审阅或最终PPT渲染。

## 来源与许可

本技能沿用原仓库的研究与写作体系，并参考公开研究、制片和排版方法；方法来源见[执行与集成](references/execution-and-integration.md)及[排版测量](references/layout-engineering.md)。参考外部方法不意味着其引擎、代码、模板或素材已随本仓库分发。

**仓库当前未声明开源许可证；外部工具与引用材料遵循各自许可。**

格式依据 [Agent Skills 规范](https://agentskills.io/specification)。安装惯例核对于 2026-10-21，参见 [Codex 技能文档](https://learn.chatgpt.com/docs/build-skills)与 [Claude Code 技能文档](https://code.claude.com/docs/en/skills)；宿主规则变化时以实际版本为准。无需把本包复制到 `AGENTS.md` 或 `CLAUDE.md`，也无需先制作插件才能按上述方式本地使用。
