# AGENTS.md — speak-understandable

这个仓库装着 stylelizer 配方库。任何会话进这里,先读完本文件再说话。

## 仓库结构

三层:基座、公共样式层、个人校准层。各目录长这样:

- **recipes/base/** — 基座。clarity(宪法加通则),必装,改动走回归集。
- **recipes/flaws/** — 病灶层,挑着装。目前:anti-ai、natural-chinese。
- **recipes/tones/** — 腔调八维:rhythm、particles、address、emotion、slang、density、rhetoric、polish。每维选一份档位,清单见 tones/README.md。
- **recipes/scenes/** — 场景层,按活挑。目前:voice-calibration、artifacts。
- **recipes/README.md** — 进门门规。
- **build/** — 个人校准层,整目录 gitignore,分发不带。combo.json 选层清单(装哪些层的单源),style.md 生成物(tools/bake.py 编译:自动路由头加全部层全文,编译期执行同维互斥),bans.md 判死词表(含具名条件列),voice.md 语气校准,personas/ 人格卡(一卡一文件,combo 的 persona 键单值点名,一次一套,分域各管——只管身份域,自称、口癖、称呼、姿态、表情库,机制维度不碰,工件和文章里不带口癖与表情),policy.json 重锚策略(钩子触发节奏的单源)。build/ 只许手写正本(combo、bans、voice、policy、personas/、TODO)和生成物(style.md、计数、旗标),严禁手抄件,初始 build/ 由 tools/init.py 从 example 生成。
- **example/** — 初始配置和个人层的复制起点。
- **documents/** — PRESETS.md 组合表,ACKNOWLEDGMENTS.md 致谢。
- **checks/** — 自检。style-conflict.md 冲突检查,cases.md 回归集,lint.py 词形判罚引擎(跟 combo.json 走:词表在"禁|改成"表格里,正则在各层的 lint 块里,装哪层查哪层,词形层不管语义病)。
- **tests/** — 纯标准库单元测试:python3 -m unittest discover -s tests。
- **tools/** — bake.py(组合编译器),init.py(初始 build/ 生成器)。
- **INSTALL.md** — 安装。
- **hooks/** — 三件,只当引擎,策略读 build/policy.json。reanchor.py(按 tiers 重锚,自带默认三级:常绳每轮一行,中绳按拍数加体格阈值全量锚,重锤压缩后立即补全量),kick.py(PostCompact 落旗标),gate.py(Stop 拦截器:判死词与漏放自评暗记打回,拦截上限可配,fail-open)。

## 分层规范

三层:base(clarity,必装,改动走回归集)、公共样式层(挑着装)、个人校准层(在 build/)。判别法:这条规则换个用户还成立吗?成立进公共层,不成立进 build/。用户摘任何东西,只动 build/ 里一个文件再重跑 bake,公共区一字不碰。每份公共配方开头必须有管辖声明:管什么、不管什么。条款必须落在声明范围内,塞进声明外的新关切就是混装——该扩声明的扩声明,该立新维度的立新维度。层间不重叠,因为每份配方的管辖声明圈定了自己的范围,一个关切只住一层。同维互斥,因为同一维度的两份档位给的是相反的指令,同时穿会互相打架,所以一次只许穿一份,编译期拦下。

元法——优先级(用户当场的话 > 宿主规则 > 配方)、同维互斥、"可以"不是配额、判断法优先于词表——在 base/clarity.md 头部的宪法里,随组合出门。本文件不重复正文,以那边为准。

受众边界:给装着配方干活的模型看的东西(宪法、规则、style.md 路由头)随组合走。给改仓库的人看的东西(本文件、recipes/README、回归集用法、致谢、测试)留在这里。判别:这行字,装配方的模型需要吗?

配方正文工具中立:不假设宿主是 Claude Code 还是别的。@ 导入、钩子这类工具特定的机制只写在 INSTALL 和 hooks 说明里,不进配方正文。

分发文档(README、INSTALL、PRESETS 这类)写完必须过自己的配方:anti-ai、natural-chinese、clarity 各扫一遍,再拿 checks/expansion-review.md 配干净上下文的子代理审一遍展开,清单改完,维护者过目才算过。去 AI 味的产品,自己的门面不许带 AI 味。
