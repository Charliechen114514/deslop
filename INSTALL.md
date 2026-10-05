# 安装（一条指针）

原则：宿主文件只加一行指针，指向你的 build/style.md。个人口味全部住在 build/（整目录 gitignore），改口味只改 build/ 里的文件，style.md 这个路径不变，所以宿主那一行一辈子不动，卸载就是删那一行。

## 第一次配置

1. 跑 `python3 tools/init.py`：从 example 生成初始 build/（combo.json 选层清单、bans.md 判死词表、voice.md 语气校准、personas/ 人格卡、policy.json 重锚策略），已有的文件不碰。改成你自己的——build/ 里只许手写正本和生成物，没有手抄件。想挂人格（狐娘这类），combo.json 加一行 `"persona": "卡名"`，一次只穿一套。然后跑 `python3 tools/bake.py`，生成 build/style.md——自动路由头加全部选中层的全文都合在这一份里，模型只读它一个。
2. 挑不准就看 [PRESETS.md](documents/PRESETS.md)，抄一组。

## Claude Code

全局（本机所有会话），在 `~/.claude/CLAUDE.md` 加一行：

```text
@/绝对路径/speak-understandable/build/style.md
```

项目级，同样一行，加进项目的 CLAUDE.md。

`@` 导入会递归展开：style.md 里指向层的指针会被继续拉进上下文。层更新自动跟上，不用重装。

## Codex 等认 AGENTS.md 的工具

AGENTS.md 没有 `@` 导入。style.md 用编译版（层的正文贴进文件），宿主加一条指令行：

```text
对话输出遵守 /绝对路径/speak-understandable/build/style.md 的全部规则。
```

## 装完必做

跑一次冲突自检：[checks/style-conflict.md](checks/style-conflict.md)。宿主已有自己的风格规则时尤其要跑。

## 机制重锚（可选，Claude Code）

长对话里模型的上下文会漂移，开头照着规则说，越往后越走样，口头约束只在开头说过一遍，所以守不住。UserPromptSubmit 钩子每 3 条消息把 build/style.md 组合的**全量配方**注入一次，这份反复注入进上下文的配方就是锚。因为每 3 条就来一次，锚永远贴着最新一条消息，长对话也冲不淡。接法：

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /绝对路径/speak-understandable/hooks/reanchor.py",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

加进 `~/.claude/settings.json`（全局）或项目的 `.claude/settings.json`，三级重锚：

- **常绳**：每条消息注入一行提示（配方在身，第一句对上用户语气），零工具调用零停顿。
- **中绳**：对话体格超过 `size_threshold`（默认 150000 字节）后，每 `every` 条来一次全量锚——强迫模型用 Read 现场读取 build/style.md 再回答，附自评指令和当轮记号。现场阅读永远是磁盘最新正本，零截断零摘要。
- **重锤**：PostCompact 钩子（hooks/kick.py）在压缩后落一枚旗标，下一条消息必定全量补锚——压缩刚把规则冲掉，下一条消息立刻补上，不留空窗。

重锚的玩法全在 build/policy.json：tiers 定什么时候触发、动作多重、说什么话，texts 定各句注入的措辞，gate 定 Stop 拦截的开关。想改中绳每几条来一次、想换注入措辞、想干脆去掉某一档，都只改这份文件，引擎一个字不用碰。另配 Stop 拦截器（hooks/gate.py）：如果模型收尾的回复里命中了判死词表，或者锚注入之后那一轮漏放了自评要求带的当轮记号，拦截器就把回复打回重写。拦截次数上限在 policy 的 gate.max_block，拦截器自身故障一律放行。换组合就改 combo.json 重跑 bake。

## 注意

- 本库让人读着舒服，不承诺躲开 AI 检测，一条都不承诺。
- 绝对路径换机器会断。换机后把仓库放回老位置，或重写那一行。
- build/ 被 gitignore，个人配置不跟着仓库走，换机自己带走。
