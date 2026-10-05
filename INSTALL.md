# 安装（一条指针）

原则：宿主文件（CLAUDE.md、AGENTS.md 这类工具配置文件）只加一行指针，指向你的 build/style.md。口味全部住在 build/ 里（整目录 gitignore），改口味只改 build/ 里的文件。style.md 这个路径不变，宿主那一行就一直不用动。只装指针的话，卸载就是删那一行。挂了钩子的话，settings.json 里挂过的也要清，文末注意一节有写。

## 准备

你需要 python3 和这个仓库的一份本地拷贝（python3 纯标准库，不用装依赖）。拷贝放在你不打算挪走的位置，因为宿主文件里写的是它的绝对路径。

## 第一次配置

在仓库根目录依次跑两条命令：

```bash
python3 tools/init.py    # 从 example 生成初始 build/：combo.json、bans.md、voice.md、policy.json、personas/
python3 tools/bake.py    # 把 combo.json 编译成 build/style.md，模型只读这一份
```

init.py 跑完你会看到 `已生成 build/combo.json（抄自 example，改成你自己的）` 这样的输出。已有的文件一概不碰，重复跑是安全的。它生成五样东西：combo.json 选层清单，bans.md 你的判死词表（AI 输出里命中即重写的词），voice.md 你的语气校准，personas/ 人格卡，policy.json 钩子触发策略。

接着改 build/combo.json。维度就是一类口味开关（称呼、密度、情绪这些），每类挑一个档，哪类没选也合法，bake 只当没意见。想挂人格（狐娘这类），加一行 `"persona": "卡名"`，单值键，一次只穿一套，写成列表 bake 直接报错。bans.md 和 voice.md 照你自己的说话习惯改。挑不动就去 [预设组合表][presets] 抄一组。

bake.py 跑完生成 build/style.md：开头一段路由头说明（告诉模型几层规则打架时按什么顺序让位）加全部选中层的全文，合在同一份文件里。加 `--check` 就只校验不写文件。选了不存在的层、维度或档位名写错、人格写成列表，都在编译期报错拦下。换层换档是改 combo.json 里一个词再重跑 bake，bans.md、voice.md、人格卡改完同样要重跑 bake，改动才进 style.md。style.md 是生成物，别手改。combo 怎么变成 style.md，机制细节看 [组合机制][how-it-works]。

## 装之前跑一次冲突检查

宿主已有自己的风格规则时（AGENTS.md、CLAUDE.md、SOP 这些），接进宿主之前把宿主规则和你的配方一起交给任意 LLM，按 [冲突检查提示词][conflict] 跑一遍，看两边打架不打架。这是装前检查，不是日常检查，配方或宿主规则有大改之后再跑一次。裁决顺序写死在提示词里：用户当场说的话 > 宿主项目规则 > 配方。

## 接进 Claude Code

全局（本机所有会话），在 `~/.claude/CLAUDE.md` 加一行：

```text
@/绝对路径/speak-understandable/build/style.md
```

项目级，同样一行，加进项目的 CLAUDE.md。

style.md 是编译产物，全文都合在 style.md 一个文件里。你换口味重跑 bake，同一路径下的内容整个换新，宿主那一行不用动。

## 接进 Codex 等认 AGENTS.md 的工具

AGENTS.md 没有 `@` 导入，style.md 又是全文编译版，宿主加一条指令行，让模型自己去读：

```text
对话输出遵守 /绝对路径/speak-understandable/build/style.md 的全部规则。
```

工具读不到工作区外的文件时，把 style.md 全文直接贴进宿主文件，效果一样，代价是换口味要重贴一次。

## 机制重锚（可选，Claude Code 专用）

一行指针只保证规则进了上下文。你在长对话里能看到模型漂：开头几轮照配方说，越往后越走样。最危险的是上下文压缩那一刻，压缩把配方全文连同旧对话一起换成一份摘要，之后的回复就没人管了。

重锚的思路是把配方在对话过程中反复送回模型眼前，你接三个钩子来配合。reanchor.py 是注入本体，缺了它整套重锚不工作。kick.py 只管压缩后补的那一锚，gate.py 只管回合收尾的体检。接法：

```json
{
  "hooks": {
    "UserPromptSubmit": [
      { "hooks": [ { "type": "command", "command": "python3 /绝对路径/speak-understandable/hooks/reanchor.py", "timeout": 10 } ] }
    ],
    "PostCompact": [
      { "hooks": [ { "type": "command", "command": "python3 /绝对路径/speak-understandable/hooks/kick.py", "timeout": 10 } ] }
    ],
    "Stop": [
      { "hooks": [ { "type": "command", "command": "python3 /绝对路径/speak-understandable/hooks/gate.py", "timeout": 10 } ] }
    ]
  }
}
```

加进 `~/.claude/settings.json`（全局）或项目的 `.claude/settings.json`。挂之前先跑完上面的第一次配置，锚的节奏和拦截器的词表都从 build/ 读。拦截器就是 gate.py，就是上面 JSON 里挂在 Stop 上的那段。

锚分轻重。轻的只注入一行提醒，零工具调用。重的叫全量锚，一次注入四样：自评指令（附一个本轮暗语，暗语是个普通词，模型要把它织进回复任意一句）、定声提醒（提醒模型开口先对上用户语气）、style.md 的路由头、强迫模型用 Read 现场读取 build/style.md 全文再回答的指令。现场读的永远是磁盘上的最新正本，你改完 combo.json 重跑 bake，下一个锚读到的就是新内容，零截断零摘要。

默认四档，按 policy.json 里的排列顺序匹配，先中的先得：

- 重锤：压缩刚结束的下一轮，不管它同时命中哪一档，一律全量锚（旗标由 kick.py 落下）。
- 开场绳：会话第一轮，全量锚。
- 中绳：对话记录体格达到 min_size（默认 150000 字节）后，每几条用户消息来一次（beat，默认 3），全量锚。
- 常绳：其余每一轮，一行轻提醒。

拦截器在回合收尾时体检最终输出：判死词命中、机械计数超限（压缩碎片、破折号限额）、全量锚注入后的那个回合没把暗语织进回复，任何一类命中就把回复打回重写。每轮拦截有上限，到上限就放行。拦截器自身出故障也一律放行，体检脚本不该把你的会话卡死。

什么时候触发、动作多重、说什么话，全在 build/policy.json：

- tiers：定有哪些锚、各自什么时候触发（when 里的触发条件，如 every_turn、beat、min_size）。
- texts：定各句注入的措辞，不覆盖的用默认。
- gate：定拦截器查什么（判死词 banned_words、暗语 score_nonce、机械计数 fragments）。
- max_block：定每轮最多拦几次（默认 1），写在 gate 块里。

想改中绳每几条来一次（beat 的数字）、想换措辞、想删掉某一档，都只改 policy.json，钩子代码一个字不用碰。档位、触发条件、开关的说明看 [重锚机制][anchoring]。

## 注意

- 编译出的 style.md 装着全部选中层的全文，常驻模型上下文，这个库比较吃 tokens。层选得越多，常驻的上下文越大。
- 本库让人读着舒服，不承诺躲开 AI 检测，一条都不承诺。
- 绝对路径换机器会断。换机后把仓库放回老位置，或重写宿主文件里那一行。
- build/ 被 gitignore，个人配置不跟着仓库走，换机自己把整个 build/ 拷走。
- 卸载就删两处：宿主文件里那一行，settings.json 里挂过的钩子。

## 参考资料

[presets]: documents/PRESETS.md
[conflict]: checks/style-conflict.md
[how-it-works]: documents/how-it-works.md
[anchoring]: documents/anchoring.md
