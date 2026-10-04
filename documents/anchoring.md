# 机制：重锚（长对话防漂移，Claude Code 专用）

配方写进 style.md 只解决"规则存在"。长对话里模型会漂移，开头照着规则说，越往后越走样。长对话里最危险的时刻，是宿主做上下文压缩（context compaction）的那一刻，因为压缩会把整段对话连同开头注入的配方全文一起换成一份摘要，而摘要之后的回复，就没有配方管着了。

重锚的思路：把配方在对话过程中反复送回模型眼前。什么时候送、送多重，由策略文件定，不由对话内容定。

## 三件钩子

- **reanchor.py**（UserPromptSubmit，每条用户消息跑一次）：按 build/policy.json 的 tiers 决定这一轮注入什么。轻的时候只注入一行提醒。重的时候注入全量锚，四个部件：score（自评指令）、voice（定声提醒）、routing（路由头）、read（强迫模型用 Read 现场读 build/style.md 全文再回答）。现场读的是磁盘上的最新正本，零截断零摘要。
- **kick.py**（PostCompact）：压缩刚结束就落一个旗标文件，下一条消息必定触发全量锚，不管当时轮到没轮到。
- **gate.py**（Stop 拦截器）：回合收尾时体检最终输出：词表命中（error 级的判死词）、机械计数超限（压缩碎片、破折号限额）、锚后轮漏放自评暗记，任何一类命中都打回重写。拦截次数有上限（默认一次，policy 的 gate.max_block），拦截器自身故障一律放行，不能把会话卡死。

## 默认策略与 policy.json

默认四档（policy.json 的 tiers，按排列顺序匹配，先中的先得）：

| 档 | 触发 | 动作 |
|----|------|------|
| 重锤 | 压缩后下一轮（force） | 全量锚 |
| 开场绳 | 会话第一轮 | 全量锚 |
| 中绳 | 对话体格超过阈值（默认 150000 字节）后，每 3 条一次 | 全量锚 |
| 常绳 | 每轮 | 一行轻提醒 |

策略的全部字段都在 policy.json，钩子代码一个字不用碰：

- when 的条件词：every_turn、beat:N、min_size:S、first_turn、force。
- action 两种：say 加文本键（注入 texts 里对应的一句），或 anchor 加部件列表。
- texts：覆盖每句注入文案，不覆盖的用默认。
- gate 开关组：enabled、banned_words、score_nonce、fragments、max_block。

想改中绳每几条来一次（beat 的数字）、想换每句注入的措辞（texts）、想干脆去掉某一档（tiers 里删一条），都只改 policy.json 这一份，钩子代码一个字不用碰。会话计数按 session 各自记（build/.reanchor-count），几个会话并行不会互相踩。

## 装法

settings.json 的接法在 [INSTALL.md](../INSTALL.md) 的"机制重锚"一节。

## 边界

钩子是 Claude Code 的机制，配方正文不带它（配方正文工具中立，任何宿主能用）。别的宿主要等效强度，得自己找事件入口，思路是通用的：轻提醒每轮常在，重锚按拍来，压缩后立刻补一次。
