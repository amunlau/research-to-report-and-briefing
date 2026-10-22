# 统一内容与证据契约

用于较长PPT、多来源比较、成套成果或持续修订。它保存研究到成品的对应关系，不是PPT渲染语言。外部引擎使用其实际支持的文件；适配层负责转换并记录映射。

## 文件与权威位置

- `.research-briefing/project.json`：范围、受众、成果、资料时点与活动路径，沿用`research-briefing/2`。
- `.research-briefing/content.json`：来源、事实、素材、报告及解析章节。结构见[账本schema](../assets/content-ledger.schema.json)。
- `.research-briefing/deck.json`：按显示顺序保存页面内容及制作映射。结构见[页面schema](../assets/deck-plan.schema.json)。
- 配置的`extensions.content_contract`可记录`ledger`、`deck`路径；正文记忆解释理由和研究过程，不另抄一套待维护数字。

小任务可用等价表格或内容卡，保留来源、判断、使用位置与状态即可。首次使用结构化文件时从实际资料建记录，不把示例内容当研究结果。只做报告时不建空PPT计划；仅制作PPT时不要求完整报告。

研究问题沿既有主线/内容卡维护；需要结构化覆盖映射时，可在账本顶层`extensions.question_coverage`记录问题ID、当前回答、回答状态、关联F/C/P ID及缺口影响。状态采用“已回答、有限回答、未解、范围外”，含义见[研究收束](research-and-evidence.md#阶段充分性与研究收束)。这是可选项目扩展，不是新增必填schema字段；不要将Q ID直接填入只接受事实或章节引用的位置。助手不验证该扩展或问题是否真正得到回答，交付前仍需逐项阅读。

## ID与状态

沿用已有ID。新项目可用S来源、F事实/判断、A素材、C章节、P页面、B页面块。B在页内唯一，以`P007/B03`定位。章节编号、实际页码、显示引用号另外映射；调整顺序不改稳定ID。原技能曾使用其他前缀，不因升级强制重编号。

事实`type`：`observation`原文报告/观察；`derived`由数据计算；`interpretation`研究判断；`assumption`假设情景。`state`描述证据：

- `supported`：在明确对象和条件内有直接支持；不意味着已经独立复现实验。
- `qualified`：可用但需要保留限制、间接证据或特定条件。
- `disputed`：存在尚未解决、足以影响结论的冲突。
- `unverified`：缺少支撑或尚未阅读核查。

假设即使计算正确，也不会转为实测事实。解释可以有强证据，仍保留解释身份。`qualified/disputed`记录`qualification`；无证据值用`null`或明确缺口，不能写0、空字符串或猜测数字。缺口可先留在研究记录，不能冒充已完成的内容块。

## 来源、事实与计算

来源记录`id/title/kind/origin/uri/read_scope`；按来源情况补日期、版本、访问时间、原件指纹、同源父ID和可靠性说明。`uri`可以是公开链接、用户提供原件的项目相对路径或真实内部定位。未允许外传的材料使用本地位置，不上传到公共检索或外部生成服务。

`read_scope`为`unread/excerpt/sections/full`。拿到标题或搜索摘要只能标实际范围。原始来源和转载分别登记，`parent_source_id`表示同源，不按两个独立证据计数。

每项事实保存：

```text
id、statement、type、state
source_refs[]：source_id、locator、support、relation
input_fact_ids[]：派生计算/解释所依赖的事实
value / unit / scope / as_of / qualification：按实际意义填写
calculation：表达式、输入、单位、舍入和结果检查记录（需要时）
```

`locator`应能回到源页、章节、图表或数据字段；网页无页码时使用章节标题、表头等。`support`用自己的话说明该处支持什么；短原文引语另按引用限制处理。`relation`取`supports/contradicts/context`，背景材料不能充当支持性证据。

推导保存输入F ID和可复算步骤，单位换算、单/双向口径、聚合范围与舍入必须明确。`calculation.checked`只记录真实复算；结构检查不会自动执行表达式。解释保存前提与推理，并保留潜在替代解释。

## 原图、数据图与素材

素材记录`id/kind/local_path/caption/source_refs/fact_ids/truth_role/review_status`。`local_path`是实际用于制作的项目相对文件路径；尚未取得原图时保留`null`及缺口，不假定远程链接已成为本地资产。

可选`sha256`绑定该A ID的`local_path`文件字节。启用`--check-files`时，助手会核对已记录的指纹；最终直接使用的素材错配报错，草稿、未使用项和仅作为派生图上游的原件错配提示。文件变化后先核对差异及受影响的审阅记录，再更新记录，不能只替换指纹就视为重新审阅。裁切或重绘形成新文件时沿新A ID保存其指纹。上游原件变化是否影响已审阅派生图的含义仍需判断；没有指纹的合法素材继续按原有来源、审阅与成品检查规则处理。

`kind`可为`original-figure/photo/table-crop/redrawn-diagram/data-chart/generated-concept/other`；`truth_role`为`evidence/explanation/decorative`。生成概念图不能标为技术事实的直接证据。复合图裁切记录`transforms`、原图号、分图与边界；同义重绘保留数据或拓扑依据及差异。

最终使用的`evidence`素材应关联支持性来源或事实，派生素材可沿`derived_from`保留这条支持链；图片文件存在、图注完整或标为`reviewed`都不能替代依据。解释性与装饰性素材按其真实用途记录，不为通过检查将承担证据作用的图改成装饰。支持链的语义是否足够，仍需实际阅读原材料。

`review_status`为`pending/reviewed/rejected`，这里的reviewed指实际检查其技术含义、裁切和可用性；最终PPT中的可读性另行检查。源图通过不等于缩入页面后可读。`reading_notes`记录系统位置、标签和关键路径，供页面与讲稿共用。裁切或重绘得到新文件时使用新A ID，`derived_from`列出原A ID，保留原件；多图合成可以有多个父素材。

派生素材不会因改名或重绘自动消除父素材的问题。父项尚未审阅或已被否决时，说明新素材如何解决裁切、可读性等具体问题；证据缺失或技术含义错误须另行补证、更正。助手会追踪上游事实与来源，但无法判断这些问题是否已真正解决。

## 页面与文本块

`deck.pages`的数组顺序就是计划页序。`deck.mode`显式记录用途，未指定时按hybrid规划；可选`deck.notes_enabled`省略时按true，用户明确关闭时写false。JSON Schema中的default仅表达约定，不会自动生成正文或备注。每页包含`id/role/archetype/title/takeaway/fact_ids/asset_ids/blocks/reading_path/speaker_notes/author_explainer_refs/density/evidence_exceptions`。

- `role`区分`title/section/core/detail/appendix/summary`；内容页围绕本次解释或论证任务组织，可以包含多个证据块。封面、章节导航与过渡页按定位和衔接安排，不强制套入技术问题；沿用现有角色枚举。
- `title`写可用的页面概要、具体问题或有据观点，并联系全场主旨。`takeaway`记录读者需要形成的核心认识或问题边界，供组织内容使用；不要求它是强结论或在页上重复打印。不放“这里填写结论”等制作指令。
- `speaker_notes`默认保存可直接照读的完整口语稿，服从本页`reading_path`和实际图表布局。普通内容页约30—90秒为初始参考，允许按复杂度与全场时长调整，不设置统一字数。只有用户关闭备注，或当前尚在规划未成稿时，才按相应状态留空；未成稿不能当作备注已交付。
- 每块有`id/kind/content/fact_ids/asset_ids/target_editability`。`content`是最终可用文字、表格数据、图注、方程或结构描述，可以是字符串或结构化对象；不把研究任务指令作为读者文字。
- `kind`区分`text/table/chart/figure/diagram/equation/source/callout`；编辑目标为`native-text/native-shape/native-table/native-chart/native-formula/image`。目标和实际导出分别记录，不能仅凭计划宣称实现。
- 页级F/A ID覆盖页面和备注所用内容；块级ID定位具体使用位置。图号/参数改变后可按块定位。关键表格单元格可在`content`内附`fact_id`，不用把每个装饰元素都建成事实。
- `reading_path`列出需依次读的B ID；图内路径放素材读图卡。`author_explainer_refs`指向C章节。
- `density`记录所选模式、字/行/表格/标签观察、字号与调整依据。它是校准记录，不是必须填满的配额。需要几何审查时，块的`geometry`采用`x/y/w/h/unit`且unit为`pt`，坐标基于`canvas.width_pt/height_pt`。

实际版面使用的点、英寸或SVG坐标由引擎换算，不把本契约中的pt直接当成另一引擎的像素。计划矩形检查保留`1e-7 pt`的舍入容差，避免大整数与浮点相加造成溢出或掩盖越界；它不验证目标应用支持的画布尺寸。文本行数、字体替换和图内标签以实际渲染为准。

同段局部加粗或着色时，`content`可选用`{"runs":[{"text":"本数据","bold":true},{"text":"仅用于测试。"}]}`。内容助手只连接同一`runs`数组内相邻的字符串`text`，忽略这些文字项的样式及备注字段；各层嵌套对象中的`style/styles/format/formatting`均作为格式元数据排除，不因该层没有`runs`而计入可见文字。非文字项或显式断行对象（`break:true`或`type`为`break/line-break/br`）会中断连接，`text`中的换行原样保留。不同段落、单元格、图节点及文本块保持独立，兄弟`caption`、`paragraphs`等正文仍分别读取。其他结构沿用独立字符串片段检查；这不是任意引擎富文本格式的通用解析器，不新增必填字段，也不证明最终页面实际可见。

图形块的`content`可保存节点、真实关系、分组及完整说明，沿用块级事实和素材关联；小任务继续用等价内容卡。构图选择、文字容量、图文对应、有效图像范围和布局调整可按[排版测量](layout-engineering.md)记于`deck.extensions.layout_records`，关联页/块ID及素材ID，需要时补实际字体与可用区域。不要在受约束的page对象上另加未经schema支持的字段；这些可选记录由制作适配使用，不使助手自动具备排版、字体测量或审美判断能力。渲染与内容保真结果保存于验收回执，避免把期望值当成实际结果写回计划。

### 可选讲述依赖记录

按[讲述路径](briefing-and-teaching.md#前提检查提到不等于解释)记录听众起点、各部分目标和真正影响理解的前提。小任务在既有内容卡中说明即可；较长PPT需要结构化保存时，可用`deck.extensions.narrative_records`，不向受约束的page对象添加`depends_on`等自造字段，也不把页面P ID塞进章节C ID的引用位置。

该可选扩展可保存：`audience_basis`（可依赖的已有基础及依据）、`route_page_ids`（本次主讲的有序P ID）、`pages`（按页ID关联理解任务、新增认识、后续用途与前提记录）。每项前提说明所需的具体认识、`established_at`中的已有基础或真实P/B位置、解释为何足够以及待补缺口；结果预告可标明后续解释位置，不当作已经建立的机制前提。字段只是项目约定，不是新增必填Schema，也无需复制完整页文、事实或另造知识编号。未采用该扩展时继续使用同义文字记录，选定一个权威位置即可。

主讲路线是`deck.pages`的有序子序列；省略路线列表时按本次约定的实际显示顺序检查。附录、隐藏页和按时长选择的路线分别确认范围；不能将未实际展示的页视为已解释。前页引用必须在本次路线更早出现，同页引用按块的`reading_path`及实际读序检查。重排、拆合、移入附录或删块后同步这些记录及首次定义位置；历史去向保留在变更记录。这里只追踪讲述依赖，事实计算的`input_fact_ids`继续承担证据依赖。

现有助手不校验`narrative_records`中的ID、顺序或语义。记录ID齐全也不证明解释充分；制作与审阅仍须对照正文、图解和真实路线检查。未来若增加自动检查，只能就显式引用、顺序和缺项报告结果，不能将其命名为“逻辑通过”。最终审阅结果记入已有回执`checks`中`id=content`的范围与发现，不增加强制评分或新的回执格式。

### 来源关联与页面展示分离

PPT默认隐藏页内书目展示，见[来源展示](visual-expression.md#ppt来源展示默认)。`source_locators`是块级追溯元数据，不意味着必须打印到页面；原F/S/A关系继续保留。`kind=source`仅在本次确需可见来源时生成，不自动为每页新增来源块。修订旧计划时先保全其来源关联，再同步移除不再显示的来源块、相应`reading_path`项和对象映射，避免悬空引用；稳定的事实与素材ID不改。

`speaker_notes`只保存完整口语稿。导出时按页块关联汇总机构/作者、标题、日期、URL或本地定位、图号/页码等真实信息，在同页备注另建“资料来源（不朗读）”分区，不覆盖口语稿，也不把文献串当作非空备注通过。无需新增page字段；展示选择保存在项目已有视觉配置，来源继续从账本派生。验收分别比对口语正文和资料分区；备注关闭时保留证据台账，不擅自恢复备注或新建未请求成果。隐藏来源不改变下方`visible_note`的可见要求。

## 未定结论的可见处理

最终使用`qualified/disputed/unverified`事实或假设时，对应页面/章节保存`evidence_exceptions`项：`fact_id/treatment/visible_note`。`treatment`为`qualified/disputed/hypothetical`：前两项分别对应qualified/disputed，assumption使用hypothetical；unverified只能用qualified明确待核并缩小判断，或转为明确的hypothetical情景。`visible_note`是实际可见的限定文字，必须出现在该页内容或该章节正文中；只放备注不够支撑读者独立判断。不使用的缺口无需制造一页“待核”。

未经核实的具体产品参数若是核心结论依据，先补证或改变结论；不能靠一句笼统免责声明继续断言。假设算例用明确的假设说明，保留单位与适用场景。最终摘要也保留决定结论的条件。

## 报告、讲稿和解析

`content.sections`保存`id/deliverable/heading/body/fact_ids/asset_ids/depends_on/evidence_exceptions`。`deliverable`区分`report/speaker-script/author-explainer`；`depends_on`可用于知识依赖。正文大时，可在项目既有文稿维护正文，并让账本仅保存有来源定位的关键内容卡；使用自动助手时提供其能够读取的内容副本并明确哪个位置是权威。

采用外部权威文稿时，章节的实际文件、标题/锚点与内容卡映射记录在现有制作记录或账本顶层`extensions`。每次审查前从当前文稿刷新受影响内容副本，并记录副本来源文件的指纹和覆盖范围；不得用旧副本的结构通过结果证明新版报告正确。报告中的引文号、图表号与最终页码分别映射回稳定S/A/C ID。账本只覆盖关键内容卡时，明确未覆盖正文仍需全文语义和引用检查。

所有成果共享事实，表达不要求逐字一致。页面保留问题、关系、证据与条件，以及讲者可沿用的解释线索；讲稿解释实际图表和转场；解析展开前置知识、中间过程与复算。禁止为了字符串一致性把报告段落原样塞进PPT。默认备注属于PPT本身，不自动增加独立speaker-script交付；用户另需独立讲稿时，从同一页ID与口语稿生成。

逐页估时按稳定页ID写入项目`presentation.timing_plan`引用的时间账，明确编辑预算与真实排练值。估算时长、来源台账和编辑提示不混入`speaker_notes`口语正文；需要附在备注区时与可照读正文分区。没有启用时间账的小任务可用等价简表，不重复维护另一份不一致的用时。

## 制作映射与变更

`engine_map`按页保存`page_id/backend/backend_version/output_path/slide_number/object_ids`。`object_ids`映射B ID到制作引擎的实际对象ID或名称；未得到可靠对象ID时为空，不制造映射。可选`route/reading_mode`记录实际引擎路线和模式，`fact_id_map/source_id_map/asset_path_map`分别保留原F/S/A到引擎编号或资源路径的映射；它们不改变上游ID。`actual_objects`按block_id记录实际`kind/detail`及必要的deviation；实际kind可为native-text/native-shape/native-table/native-chart/native-formula/raster-image/vector-image/mixed/unknown，反映检查事实。

`output_path`及`asset_path_map`的值使用项目相对路径和`/`分隔，不含盘符、反斜杠、父级跳转或控制字符；未建立的事实/来源映射项省略，不用空字符串占位。

最终映射按每个输出文件单独核对：已映射页的相对顺序应与`deck.pages`一致，映射行本身无须排序，也不强制页码从1连续起排。部分导出和不同输出文件分别处理。助手会提示部分内容块缺少对象映射、同一计划页在同一文件重复映射及声明页序颠倒；有意重排、拆分或重复展示时同步计划/变更记录，缺少可靠对象ID时继续逐块人工对照，不为消除提示编造映射。多个内容块可对应同一实际对象。这些提示不证明内容已经丢失，也不代替打开成品核对。

源计划只是引用链中间环节；要声称“最终每个数字可追溯”，还须对照最终PPT文字、表格、图像及对应源文件，核实没有导出丢失或二次改写。实际渲染与编辑检查没有执行时，留待检查，不能先填actual_objects为期望值。

内容计划与成品的对照以本次采用的计划为基线，保留有意删改/合并/拆页的去向。表格按行列语义比较，图按素材与面板比较，备注按完整正文比较；总字数、关键词或对象数量相同不能证明语义保留。检查方法见[质量与版本](quality-and-versioning.md)。

更正F、A或S后，沿sections/pages/blocks列出影响位置，标记待同步；调整版式不会自动推翻无关研究。引擎重编号只改映射和实际页码。页序或主讲路线变化时，另按[重排同步](briefing-and-teaching.md#排版前审阅与重排同步)复查理解前提、首次解释和全部受影响的后续使用，更新目录、备注转场、时间账与附录入口；仅更新页码不代表叙述同步完成。最终文件哈希、渲染输入和实际查看范围见[质量与版本](quality-and-versioning.md)。

## 只读助手

必需文字与ID的非空白约束由Schema中的显式`pattern`表达；`minLength`按原字符串字符数检查，不隐式去除空白或改写ID。可空草稿字段仍按各自定义处理，备注的最终完整性要求另行检查。路径禁止控制字符，避免计划记录通过后才在文件生成时失败。

```text
python <skill-dir>/scripts/audit_content.py --root <project-dir> --ledger .research-briefing/content.json --deck .research-briefing/deck.json --stage draft
python <skill-dir>/scripts/audit_content.py --root <project-dir> --ledger .research-briefing/content.json --stage final --check-files
```

助手查必需结构、ID与引用、来源定位、派生依赖、限定说明、素材文件和页面映射；输出发现，不改原文件。`final`提高所用内容的完整性要求。备注启用时，空白`speaker_notes`在draft阶段提示，在final阶段报错；显式关闭时允许为空。非空仅通过这一结构条件，不能证明讲稿完整、可照读或已经写入PPTX。它不判断原文是否支持论断，不执行计算表达式，不保证语义覆盖，也不验证引擎输出与计划相同。JSON Schema供可用验证器使用；内置助手执行所说明的结构子集与跨文件检查，不能冒称完整Schema验证或事实审计。

最终已用的证据素材缺少支持性来源或事实链时，助手报错；派生链可提供继承依据。草稿或未使用项仅提示，解释性/装饰性素材不要求同一门槛。这仍是引用结构检查，不证明原图或事实真正支持成品中的论断。

核对最终文件时，可用`inspect_pptx.py --pptx <final.pptx> --include-text --out <new-inventory.json>`取得各页`native_text.text/paragraphs`与`notes.text/paragraphs`。原生段落按XML顺序提取，保留段落和显式换行；不推断视觉读序，也不还原项目符号、公式结构或图片/图表内文字。备用显示分支和隐藏对象的文字可能一并提取，命中字符串不证明它在页面上可见。`characters`沿用文本节点字符合计，不计补入的分隔换行，可能不同于完整文本长度。输出路径必须是新文件。将这份材料与计划逐页比对，缺失部分仍回到实际页面或对应对象检查。
