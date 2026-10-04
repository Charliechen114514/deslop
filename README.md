# speak-understandable

## TL; DR

把 AI 的 **说话** 输出调成你要的风格。

> Hint: 
> 1. 这个README其实就是不说人话的 GLM 5.3 写的。。。
> 2. 这里提醒一下，这个仓库比较吃tokens，因为编译出来的 style.md 装着全部选中层的全文，会常驻在模型的上下文里。笔者发现对于一些自己就说不好人话的AI必须进行强力的约束，不过可以适当调整仓库内部的约束策略。对于聪明的模型，自身就说人话，那就没必要用咯╮(╯▽╰)╭

## Why this?

是，GitHub 上已经有很多 humanizer（把 AI 写的东西改得像人写的，虽然说真的也不咋像），但只有"像人"一种风格。这个仓库做的是另一件事，stylelizer（风格调配库）：你说要什么风格，它就调成什么风格。"说人话"只是其中一种口味。

直接跟模型说一句"请说人话"，能顶一会儿，顶不了长对话。对话一长，模型的上下文会漂移，开头还照着要求说，越往后越走样。一种口吻实际是几十条细则（哪句该删、哪个词禁用、语气词跟谁走），口头说一遍等于丢一遍，写下来才每次都在。

所以，这里攒的是配方：规则写成一层一层的文件，你照口味挑着组合，编译（bake）成一份模型只读的 style.md。

## 来试一下

你需要 python3，然后让AI在仓库根目录跑三条命令：

```bash
python3 tools/init.py    # 生成 build/：combo.json、bans.md、voice.md、policy.json
# 改 build/combo.json，每个维度挑一个档（挂人格卡就加 "persona": "fox-girl"）
python3 tools/bake.py    # 生成 build/style.md，模型只读这一份
```

combo.json 挑层，bans.md 放你自己的禁用词，voice.md 让它学你说话，personas/ 放人格卡（狐娘这类，一次挂一套），都在 build/ 里改，policy.json 是钩子触发策略，装了钩子才碰。整个目录 gitignore，不跟着仓库走。

生成的 style.md 装进宿主只要一行指针。Claude Code 加一行 @ 导入，Codex 等认 AGENTS.md 的工具加一行指令，具体在 [INSTALL.md](INSTALL.md)。懒得挑口味，抄 [PRESETS.md](documents/PRESETS.md) 的一组。

## 仓库里有什么

- [recipes/](recipes/) — 配方正本，四区。base/ 基座（clarity 管说清楚，必装）、flaws/ 病灶（AI 味、翻译腔，挑着装）、tones/ 腔调（八个维度，每维选一档）、scenes/ 场景（按活挑）。
- [build/](build/) — 你的私人目录，combo.json、人格卡和生成物都在这里，整目录 gitignore。
- [example/](example/) — init.py 的模板，初始配置和个人层从这复制。
- [tools/](tools/) — init.py 生成初始 build/，bake.py 把 combo.json 编译成 style.md。同维选两份会直接编译失败，错误在编译期拦下。
- [checks/](checks/) — 自检三件。lint.py 词形判罚、cases.md 回归集、style-conflict.md 冲突检查。
- [hooks/](hooks/) — 长对话防漂移的钩子三件（Claude Code 专用），触发策略在 build/policy.json。

combo.json 怎么编译成 style.md、防漂移的钩子怎么配合、自检怎么跑，看 [documents/](documents/)。

## 想改配方

加一层、加一条规则、报一个病句，可以看看 [CONTRIBUTING.md](CONTRIBUTING.md)。配方区自己的门规在 [recipes/README.md](recipes/README.md)。

## 边界与致谢

这套配方按中文写的，管中文输出。管的是读着舒服，**不承诺躲开 AI 检测，一条都不承诺。所以拿这个混论文的，别想咯┑(￣Д ￣)┍，右转humanizer哦**

来源与致谢在 [ACKNOWLEDGMENTS.md](documents/ACKNOWLEDGMENTS.md)。MIT License。
