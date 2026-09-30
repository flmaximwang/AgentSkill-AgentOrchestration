# AgentSkill-AgentOrchestration

Agent 协作类 skill 的合集。本机上每个 Hermes profile 是 Discord 里一个独立的 bot（各自的 `skills/`、
`memories/`、`cron/`），用户一个人编排它们：一个 bot 产出经验/简报，另一个负责构建或评审。这里放的是
**这套协作本身**的程序——分工判定、交接件、产物自检、独立复现、落地门，以及跨 agent 的 git 纪律。

**public 仓库**：内容与任何具体 profile 无关，可分享。

## 索引

| skill | 用途 | 可执行入口 |
|---|---|---|
| [agent-to-agent-handoff](skills/agent-to-agent-handoff/SKILL.md) | **构建方一半**：别的 agent 把任务或经验简报交给你时的全套流程——先钉死自己是谁 → 整篇读完 handoff → 按验收清单机器自检 → 重测对方报的数字 → 经文件系统交回 | `scripts/check_skill_package.py <skill-dir \| repo-root>` |
| [agent-handoff-and-review](skills/agent-handoff-and-review/SKILL.md) | **两侧全程**：分工与验收的程序（产出方写交接件 / 构建方复核 / 评审方独立复现 / 落地门），外加跨 agent 的 git 纪律与「把对方 profile 里的改动迁回仓库」的 Step 6 | `templates/handoff-brief.md` |

装进 Hermes（三段式标识符，按仓库内路径，**不需要 tap**；`--category` 只决定落点）：

```bash
for s in agent-to-agent-handoff agent-handoff-and-review; do
  hermes skills install "flmaximwang/AgentSkill-AgentOrchestration/skills/$s" --category agent-orchestration -y
done
```

安装时会 pin 到当时的 commit，之后 `hermes skills check` / `hermes skills update <name>` 直接可用。
`--category` **只在安装时读取**：换分类 = uninstall + 带新 `--category` 重装。skill 目录是 per-profile 的
（`$HERMES_HOME/skills/`），另一个 bot 要用就在那个 profile 里重跑同一条命令：
`hermes -p <profile> skills install …`。

**当前状态：** 默认 profile + 10 个命名 profile 都已按 `--category agent-orchestration` 装（hub 安装，有
lock 条目，rev 随 main）。**本仓库是它们唯一的 source of truth**：改内容改这里，`git push` 后
`hermes skills update <name>` 取新版。

> 未决：`agent-handoff-and-review` 在默认 profile 里还留着一份**本地副本**
> （`skills/autonomous-ai-agents/agent-handoff-and-review`，无 lock 条目，由另一个会话的 curator 在写）。
> 两份同名并存会漂移；是否退役那份本地副本待用户拍板。

## skills/agent-to-agent-handoff

两个（或更多）agent 共担一个任务时的固定动作，解决三个真实故障：一条 @ 提到多个 bot 时**每个 bot 都收到**
同一句指令，于是双方都以为那是自己的活；handoff 里的数字在简报写完到落地之间已经漂了；以及「产出计划」
被当成「交付产物」。

- **Step 1 先判定我是哪一方**：从 `gateway_state.json` 读本次网关服务的 profile，再用每个 profile 自己的
  bot token 问 Discord `/users/@me` 拿身份（只管道过滤后的 JSON，绝不回显 token），最后从本 profile 的
  `logs/agent.log` 里用入站消息文本或 thread id 反查 `session=` 把自己钉死。对称时用不对称证据：谁的会话
  承载了原始请求、谁的 profile 产出了已有产物、用户在回答谁的报告。
- **Step 2 整篇读完 handoff**：handoff 常分片到达（`(1/2)` / `(2/2)`）+ 仓库里一个长文件；**包括**它的
  「我没核实的东西」那一节——纠正就是从那里来的。
- **Step 3 按验收清单构建，并用代码自检**（`scripts/check_skill_package.py`，逐项 pass/fail、非零退出）：
  目录名 == frontmatter `name`；`description` 前 ~57 字符自带路由信号；frontmatter 可解析、没有未填的占位
  标记；每个 `references/…` 链接都能落地；skill 包交付物还要先本地预测 `skills_guard` 判决并写成 verdict。
- **Step 4 复核 handoff 自己的声明**：把它的数字**从活的取源上重测一遍**再写进产物，逐条列出「我的测量值
  vs 它的值 + 我测量的位置」。预期漂移：文件数/行数变了；同一文档里后文的发现推翻了前文的提醒；「当前状态」
  一节被后续修复作废；文档描述的 flag/默认值被更新的实测推翻。
- **Step 5 交付后守住角色**：产物**经文件系统**（共享仓库）交回，不走聊天散文——评审方要 diff 不要摘要；
  汇报用固定的四段式（被要求做什么 / 做了什么 / 效果+实测数字 / 还剩什么），纠正清单领跑效果段；不自评通过、
  不替用户回答路由给用户的开放问题；没做的事直说（未 push 的 commit、未跟踪的产物、没跑的工具）。
- **所有权与并发**：只本地 commit，双方+用户都同意后才 push，commit 按逻辑单个切；**永不提交对方的产物**
  （留作未跟踪并说明）；共享 clone 里按 pathspec `git add`（对方的未 push commit 和未提交改动会被 `-A` 卷进来）；
  改对方也可能动的文件前先 `git status` + `git fetch`，覆盖可能领先的副本前先 diff。
- **坑**：网关会把自己的进度贴进 thread（读起来像对方的消息——按 author id 归属，别按内容）；计划不是交付；
  一个 false `caution` 判决通常是文档写法造成的（`inline_shell_exec` 模式 = 叹号+反引号+一个非空字符+反引号，
  所以「以叹号结尾的字面量被反引号包住、紧跟另一个 code span」会命中——把这类字面量的反引号去掉再重扫，
  绝不用 `--force` 绕过）；「这一节保持原样」优先于你的文风偏好；一个项目实例里的数字是证据不是常数，每个
  实测数字都要标它来自哪个实例。

> 本 skill 自带一个可执行自检脚本（上表那条）。改内容改本仓库的 `skills/agent-to-agent-handoff/`，
> push 后装过它的 profile 跑 `hermes skills update agent-to-agent-handoff` 取新版（没装过就先跑上面那条
> install）。扫描判决（`tools/skills_guard.scan_skill`）：`safe`。

## skills/agent-handoff-and-review

**两侧全程**的那一份：把「分工与验收的程序」写全——不是内容质量，而是谁出什么、谁核什么、什么时候才允许
push / 安装 / 删除。四条不变式：产出方出交接件（任务书 + 边界 + 素材出处 + 验收清单 + 待用户拍板项）；构建方
不抄数字（每个统计量自己连源复核，对不上按实测写并出更正清单）；评审方独立复现（逐条核清单、数字自己跑、
意见分 P0/P3）；**落地门**（push / 安装 / 上线 / 删除要两侧点头 + 用户显式同意，之前只停在本地 commit）。

- **Step 1–2 产出方与构建方**：交接件骨架六节（任务书 / 边界 / 素材出处 / 验收清单 / 待用户拍板 / 交接方式），
  附 `templates/handoff-brief.md` 可直接复制；构建方先做最小只读探针复核再动手，实例数字一律标注归属。
- **Step 3 交还前自检**：结构（YAML、目录名=name、description 短且自含触发、相对链接存在）+ 本地预测
  `skills_guard` 判决（`safe` 才能裸装）+ **两类假阳性陷阱**（叹号/反引号并写命中 `inline_shell_exec`；
  home 相对字面路径写 ssh 配置/密钥名命中 `ssh_dir_access`）。
- **Step 4 评审方**：逐条核、数字自己跑、意见分级、先确认被审对象的 commit/版本号、通过就明说。
- **Step 5 落地门**：默认停在本地 commit；退役重复副本先 `tar` 备份再删；改名/迁移的波及面（remote、README
  安装路径、仓库 description 一处不漏）。
- **Step 6 把另一个 agent 的改动迁回仓库**：先 `diff -rq` 定位漂移再逐字节复制（**照抄不重述**）；仓库
  README 索引同一条 commit 一起改；只 `git add <paths>`；push 前 `fetch` + 点数；`update` 打印
  `Skipping … local edits` 是预期，刷新到新 HEAD = 同一条 install 带 `--force`；收尾用
  `hermes -p <profile> skills check <name>` = `up_to_date` 验收，并**逐个 profile** 查 lock。
- **共享一台机器的纪律**：同一线程可能挂着两个 bot（先拉线程历史）、不吞对方的未提交文件、一步一条 commit、
  写前重读、共享长跑服务重启要打招呼、过程文档与交付物分目录、决定记录落盘。
- **反例黑名单**：自改自评、把对方数字当事实、没两侧点头就 push/安装/删源、为「更通用」删掉实测证据、
  同一知识两处并行维护、把 @ 另一个 bot 的消息当成自己的活、顺手提交对方的未跟踪文件、评审只写「建议优化」。

> 迁移说明：本 skill 原为默认 profile 的本地技能（`skills/autonomous-ai-agents/agent-handoff-and-review`，
> 无 lock 条目），迁入本仓库时只做了一处**为过扫描闸**的改写——把正文里两处 home 相对字面路径的 ssh
> 配置/密钥名改写成文字描述（`ssh_dir_access` 是 high，community 源上会拦安装），语义未变。
> 装进 Hermes 的命令见上面的安装块；扫描判决：`safe`。
