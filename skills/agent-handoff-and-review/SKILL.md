---
name: agent-handoff-and-review
description: "Use when work is split with another agent or profile."
version: 1.0.0
author: hermes-curator
license: MIT
metadata:
  hermes:
    tags: [multi-agent, handoff, peer-review, acceptance-checklist, shared-host, git-hygiene]
    related_skills: [hermes-agent, maintain-hermes-skills]
---

# 与另一个 agent 分工、交接、互审

两个 agent（或两个 profile 的两个实例）在同一台机器上做一件事、用户要求"两方都满意"时走这套。它管的不是内容质量，是**分工与验收的程序**：谁出什么、谁核什么、什么时候才允许 push / 安装 / 删除。

## When to Use

- 用户把一件事拆给两个 agent（"你把经验总结出来交给它建 skill""建好后交还给你审，直到两方满意"）。
- 你拿到另一 agent 的产物要出审查意见，或你的产物被对方审。
- 用户在两个 bot / 两个 profile 之间来回指挥同一条流水线（同一台机器、同一个仓库/服务）。
- 用户说「A 改了它的 \<skill\>，把改动迁移到 \<repo\>，commit，push，update」——另一个 agent 的改动要落回共享仓库时，走 Step 6。

## 不变式（四条，别省）

1. **产出方出「交接件」**：任务书 + 边界 + 素材出处 + 验收清单 + 待用户拍板项。没有验收清单就没有可核的合同。
2. **构建方不抄数字**：对方写的每个统计量都要自己连源系统复核一遍；对不上就按实测写，并在交接件里列出更正。
3. **评审方独立复现**：验收清单逐条核，数字自己跑（不采信对方的自述）。
4. **落地门**：push / 安装 / 上线 / 删除，要**两侧都点头 + 用户显式同意**；在此之前只做本地 commit（磁盘上的可回退状态）。

## Step 1 · 产出方：写交接件

用 `templates/handoff-brief.md` 起稿。六节缺一不可：

| 节 | 内容 | 判据 |
|---|---|---|
| 任务书 | 要建/改什么、完成意味着什么 | 每一条都能被第三方验证「做了没有」 |
| 边界 | 什么不许写成通用常量、什么名词不许发明 | 防止把实例数字写成规范 |
| 素材出处 | 可复核的路径/命令 | 对方能自己跑出同样的结论 |
| 验收清单 | 逐条可核（名字与路径、通用性、数字可追、报错原文、阶段不混、链接可解析…） | 清单就是后续评审的合同 |
| 待用户拍板 | 收敛到 ≤3 件，每件给「回什么就能推进」 | 别把决策摊成一张菜单 |
| 交接方式 | 谁在什么时候做什么、交还给谁 | 写清「建好→自查→交还→我审→两侧满意→用户拍板」 |

**硬约束**：写进交接件的数字/报错原文/路径必须是**实测**的、能追到出处；没实测过的标「待核」。推测会被下游当成事实照抄——这份材料会变成对方的事实源。

## Step 2 · 构建方：先复核，再动手

1. **连源系统复核**（数据库、服务、仓库都自己连一次）。顺序：最小只读探针（数据库 `SHOW` / `SELECT`；文件系统用 `search_files (target='files')`；仓库 `git status` / `git log`）→ 统计量 → 才写产物。
2. **对不上的地方按实测写，并列成更正清单**（「素材写 X / 实测 Y / 判据」）。这比默默改掉有价值：产出方能改它的材料。
3. **只做交接件里写的事**；冒出的设想先问，不自行发挥。
4. **实例数字一律标注归属**（「实例 `zsqlab08`：42 管 / 162 槽位」），不写成通用常量。
5. 「本机细节 vs 可移植规范」的判据是**可移植性**：真实路径、端口、账号、脚本落点不进 skill 正文，落到该对象自己的记录里（项目 vault / 仓库 `docs/`），正文只留可迁移判据 + 一组实测向量。

## Step 3 · 交还前自检（交付物是 skill 时）

- **结构**：YAML 可解析；目录名 = frontmatter `name`；`description` 自含触发词且短（索引会截断长描述）；正文里每个 `references/…`·`scripts/…` 相对链接都存在（写个脚本批量核，别用眼睛）。
- **扫描闸预测**（装得进去才算交付）：
  ```bash
  hermes-agent/venv/bin/python3 -c "import sys; sys.path.insert(0,'$HOME/.hermes/hermes-agent'); \
  from tools import skills_guard; from pathlib import Path; \
  r=skills_guard.scan_skill(Path('<skill 目录>'), source='community'); \
  print(r.verdict, [(f.pattern_id, f.file, f.line) for f in r.findings])"
  ```
  `safe` 才能裸装；`caution` / `dangerous` 在 community 源会被策略拦下（要 `--force`，不要靠它）。**改文本，不要用 `--force` 掩盖**。
- **假阳性陷阱（实测）**：扫描闸的 `inline_shell_exec` 规则是「`!` + 反引号 + 非空 + 反引号」。把以 `!` 结尾的词放在反引号里、紧跟又开一个反引号 span（例如两个 Excel 错误值并写）就会命中 ⇒ 错误值**不要包反引号**。
- **假阳性陷阱（第二类）**：把本机 ssh 客户端配置或密钥文件写成 home 相对的字面路径命中 `ssh_dir_access`(high)——community 源上**两条就足以**把 verdict 从 `safe` 压到 `caution`、安装被拦。改写成文字描述（「本机 ssh 客户端配置里已有 Host …」「专用密钥由 `IdentityFile` 指向」）即回到 `safe`：Host / IP / 用户名照留，密钥文件名不必写出来。
- **交还话术**：一句「建好了，请审」+ 4 段式汇报 + 逐条对验收清单的自查结果 + 仍未定的少数决策。

## Step 4 · 评审方：独立复现，分级出意见

1. **逐条核验收清单**，每条写清「怎么核的」（命令/探针），不写「我认为」。
2. **数字自己跑**：连系统复现对方的每个统计量，不采信自述。**对方指出你的素材写错时，明确承认并给更正值**。
3. **意见分级**：`P0` 阻塞（改完再走）vs `P3` 不阻塞（可随下一轮带过）；每条写「改哪一处 + 为什么 + 怎么验证」，不写「建议优化」。
4. **通过就明说**「通过 + 同意进入下一步」；不通过就给可执行的返工清单，别写情绪化总评。
5. 评审前先确认被审对象的 **commit / 版本号**并写进意见（否则后续没人知道审的是哪一版）。

## Step 5 · 落地门

- 两侧都点头 + 用户显式同意，才 push / 安装 / 上线 / 删源。**默认停在本地 commit**。
- 安装/发布命令写全（例：`hermes skills install "<owner>/<repo>/skills/<name>" --category <cat> -y`），并说明安装会 pin 到当时 commit、之后 `check` / `update` 才可用。
- **退役重复副本**：合并后把冗余那份删掉（先 `tar czf` 备份到 scratch，再删，并在决定记录里写明备份路径）——两份并存必然漂移。
- 改名/迁移的波及面：`gh repo rename` 之后必须同步 `git remote set-url` + README 里的安装路径段 + 仓库 description；漏一处就是「README 指向 404」这类名实不符。

## Step 6 · 另一个 agent 改了自己那份副本：迁回 source-of-truth 仓库

用户说「A 改了它的 \<skill\>，把改动迁移到 \<repo\>，commit，push，update」时走这条。仓库是唯一真源，profile 里那份只是安装副本；通用 update 语义见 `update-hermes-skills`，这里只记跨 agent 的那几处。

1. **先定位差异，别重写内容**：`diff -rq <profile 副本> <clone>` 找出漂移的文件，把副本**逐字节复制**到 clone（`shasum -a 256` 两边相等为准）。改动是对方写的——**照抄不重述**，重述会把实测证据改成概括。
2. **仓库的索引/README 一起同步**：README 若逐条概括了该 skill 的正文，只改正文就是名实不符。同一条 commit 里交，并在汇报里点明「我动了 README」以便回退。
3. **只暂存自己的路径**：`git add <paths>` 点名，绝不 `-A`。对方的会话常在同一个 clone 里留下未跟踪的过程文档——**不要顺手提交**，列出来让他拍板。
4. **push 前对齐并点数**：`git fetch` + `git status -sb`；fast-forward 且区间内只有自己的 commit 时，汇报里明说「没夹带别的会话的 commit」。
5. **`update` 打印的 `Skipping: … you have local edits` 是预期的**，不是故障：update 比的是**磁盘 vs 记录哈希**，而副本刚刚就是新内容。**改成「重新安装」时会被直接拒绝**：`Warning: '<name>' is already installed at <cat>/<name>. Use --force to reinstall.` ⇒ 刷新到新 HEAD = 同一条 `hermes skills install <identifier> --category <cat> -y --force`（`--category` 每次都得重给）。
6. **`--force` 只在第 1 步已让副本 == 上游时才安全**：它 `rmtree` 整目录替换，副本里凡上游没有的文件都会丢。按之前再 `diff -rq` 一次（对方可能仍在写），按之后必须仍然为空。
7. **验收**：`hermes -p <profile> skills check <name>` = `up_to_date`；install_path 与 category 未变（update 不重新归档）；lock 条目的 `scan_provenance.source_url` 指向新 commit、`content_hash` 已刷新。lock 文件顶层键是 `installed`（不是 `skills`）；**只有装了它的 profile 才需要 update**，逐个 profile 的 `skills/.hub/lock.json` 点名查，别在一处改完就宣布全机同步。
8. **「要迁的东西不在仓库里」先判身份，再决定迁哪一份**——判错会让整轮迁成空转：`<profile>/skills/.hub/lock.json` 里有它 ⇒ 那是 **hub 安装副本**（迁它 = 把内容给它的真实源仓库，装回去走 install / update，不是从 profile 直接拷）；无 lock 条目 ⇒ **本地技能**，单独列出来问要不要一起迁，别替他决定。用户点名的仓库还可能只是 live profile 的**滞后快照**：`Agent-<Name>` 这类分发仓库由 `distribution.yaml` + `scripts/sync.py check` 驱动，`check` 只会告诉你 push 会新增哪些路径，仓库里当然找不到新 skill，实体在 `<HERMES_HOME>/profiles/<profile>/skills/<category>/` 下。
9. **快照前确认没有别人正在写**：`tail <HERMES_HOME>/profiles/<profile>/skills/.curator_ledger.jsonl`（每条带 `session_id` 与改动前后的 sha256）配合文件 mtime，判定这个 skill 是否仍被另一会话改；**快照放最后一步**，并在汇报里写明「取自 <时刻> 的副本、sha256 若干」——否则装进去的版本几分钟后就不是最新的了。
10. **两侧内容都要落定时以实测定方向**：profile 副本常年被 runtime / curator 追加，可能比仓库新；`diff -rq` 与 `shasum -a 256` 是唯一判据，方向错了就是把对方刚写的实测证据退回去。

## 共享一台机器的协作纪律

两个 agent 共用同一份文件系统、仓库，乃至长跑服务：

- **同一条聊天线程里可能同时挂着两个 bot**：动手前先拉线程历史（`discord action=fetch_messages`，`channel_id` 用线程 id）——看清这条消息点的是谁、另一个 agent 已经做到哪一步。用户说「他改了他的 X」时主语是另一个 profile：那是它的活，别重做，也别把它的在制品当自己的交出去。**自己 profile 的 `session_search` 看不到对方的会话**（对话存在对方 profile 的库里），要还原它的现场就读那条线程，或以该 profile 读会话。
- **不要吞掉对方的未提交文件**：动手前 `git status`；`git add` 只用 pathspec 点名自己的路径，别 `-A`。
- **提交前看清暂存区**：对方已 `git add` 的重命名会被你下一条 commit 一起带走 ⇒ 要么先按主题拆好，要么在汇报里点名。**一步一条 commit**。
- **文件可能被对方改过**：写前重读（覆盖写被拒不是故障而是保护）；产物被 mv/rename 后，按旧路径的读写都失效 ⇒ 换新路径重新读一次。
- **共享的长跑服务**：重启前打招呼，或事后立即说明影响（如「客户端需重连」）。诊断「服务坏了还是数据坏了」的最快判据是**把数据复制到 scratch 独立跑同一命令**：副本正常 ⇒ 是服务/会话状态，重启而不是调试数据。
- **过程文档与交付物分目录**：交接件、评审意见、决定记录进 `docs/`；交付目录只放交付物；README 用一行写明哪些是过程记录。
- **决定记录**：把「用户的决定 + 执行结果 + commit 号 + 剩余待办」写成一份文件（含未答项）——别让状态只活在聊天里。

## 汇报偏好（给用户）

- **4 段式**：要什么 / 做了什么 / 效果 / 待办；结论先行，数字与报错原文照贴。
- 收口时只留 ≤3 件要他拍板的事，每件写「回什么就能推进」。
- 他明确拒绝"备选方案"清单：某条正路被堵时先找官方机制（官方文件格式/flag/上游修复）把那条路打通，别自造兜底；绕路的代价要明说。
- 成篇的分节长报告他会说"看不懂"：先给一句结论 + 他要做的那一件事，细节往下排。

## 反例黑名单（不要做）

| 不要 | 为什么 |
|---|---|
| 同一个 context 里「自己改自己评」 | 改完立刻自评必然乐观偏差；评审必须是另一侧、独立复现 |
| 把对方的数字当事实照抄 | 对方的材料同样会有旧值与自相矛盾（实测同一份材料里 4 处数字与现况不符） |
| 没两侧点头就 push / 安装 / 删源 | 落地不可回退，用户也没拍板 |
| 为「更通用」删掉实测报错原文与具体数字 | 那些原文是交付物的价值所在；通用化不是删证据 |
| 同一份知识两处并行维护 | 必然漂移；合并后必须退役冗余副本（先备份） |
| 把线程里 @ 另一个 bot 的消息当成自己的活 | 一个线程两个 bot 并存，重做等于拿自己的产物覆盖对方的在制品 |
| 顺手提交/删除对方留下的未跟踪文件 | 那不是你的产物；先列出来让他拍板 |
| 评审里只写「建议优化」 | 没有可执行判据，等于没审 |

## 参考

- `templates/handoff-brief.md` —— 交接件骨架（含验收清单写法），复制改。
