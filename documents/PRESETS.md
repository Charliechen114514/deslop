# 预设组合表

组合就是把挑好的层写进 build/combo.json，在仓库根目录跑 `python3 tools/bake.py`，生成 build/style.md 给模型读（写法见 [example/][example]，build/ 整目录 gitignore，不跟着仓库走）。style.md 是生成物，你别手改它，改口味就是改 build/ 里的文件，再重跑一次 bake。你懒得挑的话，直接从下面抄一组。

挑法一共六条，下面逐条说：

- 基座 clarity（说清楚的宪法）必装，这一层不用挑。
- 病灶层治什么挂什么，AI 味重挂 anti-ai，翻译腔重挂 natural-chinese。
- 腔调有八个维度，每个维度各选一份档位。
- 场景层按你常干的活挑，常写 commit、README 就挂 artifacts。
- 个人层是 combo.json 的 personal 键，装 build/ 里的 bans.md 和 voice.md，照你自己是谁写。
- 人格卡想挂就挂一套，狐娘这类。

层的机制、combo.json 怎么编译成 style.md，你看 [组合机制][how-it-works]。

| 组合     | 适合谁                                       | 层                                                                                                                                                                                      |
| -------- | -------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 松弛对话 | 日常搭档。要清楚，要治 AI 味和翻译腔，语气跟人走，节奏松弛不赶 | clarity + anti-ai + natural-chinese + rhythm-mixed + particles-follow + address-follow + emotion-light + slang-follow + density-full + rhetoric-plain + polish-raw + bans + voice（个人层） + artifacts |
| 工程默认 | 快节奏干活，信息密度优先，语气词和情绪全关   | clarity + anti-ai + rhythm-tight + particles-off + address-off + emotion-off + density-tight + rhetoric-plain + polish-finished + artifacts                                             |
| 极简     | 只求说清楚，别的口味都不要                   | clarity                                                                                                                                                                                 |
| 代写专用 | 常替人写邮件、帖子，按对方平时的文字定口吻   | clarity + voice-calibration + anti-ai + density-full（按底样定）                                                                                                                        |

这四组的骨架，你扫一眼就能看出规律。松弛对话跟着用户走：语气词、称呼、俚话都装跟走档（particles-follow、address-follow、slang-follow），情绪进场一点（emotion-light），节奏交错（rhythm-mixed），密度舒展（density-full），边角允许毛糙（polish-raw），两个病灶层都装上，是日常搭档的默认口味。工程默认往收紧的那一侧拨：节奏紧凑（rhythm-tight），语气词、称呼、情绪全关（particles-off、address-off、emotion-off），密度紧凑（density-tight），收尾工整（polish-finished），只留 anti-ai 治病。两组的修辞都取素面（rhetoric-plain），比喻默认不打。极简只装基座，宪法和通则管说清楚，别的维度一概不选。代写专用挂了 voice-calibration 场景层，口吻按底样（对方平时的文字）定，密度也跟着底样走。

表里写"bans + voice（个人层）"，指的是 combo.json 的 personal 键装上 build/ 里的 bans.md 和 voice.md。你要改判死词表，动 bans.md，要改语气校准，动 voice.md。表里的 artifacts 是场景层的工件档，管 commit、README、发布说明这类落地文件。出厂的 example/combo.json 就是松弛对话那组，只差完成度（polish）一维没选，bake 对没选的维度只提示没意见，合法。

抄的时候把表里的层照着写进 build/combo.json，bake 一下就有 style.md。装进宿主的接法看 [INSTALL.md][install]。

[example]: ../example/
[how-it-works]: how-it-works.md
[install]: ../INSTALL.md
