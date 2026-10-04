# 机制：样式如何组合（从 combo.json 到 style.md）

## 三层模型

- **基座**（recipes/base/clarity.md）：必装。说清楚的通则，加整个组合的宪法（优先级、同维互斥、"可以"不是配额、判断法优先于词表）。
- **公共样式层**（recipes/flaws、tones、scenes）：病灶层挑着装，腔调层每个维度选一个档位，场景层按活挑。
- **个人校准层**（build/，整目录 gitignore）：判死词表 bans.md、语气校准 voice.md。换人用，整份换。

一条规则住哪层，判别法就一句：换个用户还成立，进公共层。不成立，进 build/。

## 选层清单 combo.json

```json
{
  "flaws": ["anti-ai", "natural-chinese"],
  "tones": { "rhythm": "mixed", "particles": "follow" },
  "scenes": ["artifacts"],
  "personal": ["bans", "voice"]
}
```

- flaws：装哪些病灶层，写文件名。
- tones：腔调各维度选哪个档。维度是文件名前半（rhythm、density 这些），档位是后半（mixed、full 这些）。加新档写新文件就行，不用登记，编译器扫描目录自动认。
- scenes：场景层。
- personal：个人层文件名（不带 .md），从 build/ 取。

基座不用选，永远在。

## bake.py 做什么

`python3 tools/bake.py` 把清单编译成 build/style.md，另配 `--check` 只校验不写文件。编译期拦三类错：选了不存在的文件、未知的维度或档位名，直接报错。腔调层的互斥是靠数据结构本身保证的：因为 combo.json 里每个腔调维度只有一个键，一个键装不下两份层文件，所以想在同一个维度下装两份，在清单层面就写不进去，根本轮不到编译器去拦。哪个维度没选，提示"没意见"，合法。

bake 出来的 style.md 分两部分。开头一行是路由头，从各层标题现场拼装，并写明冲突时谁赢。后面是全部选中层的全文。两样东西编译时剔除：各层的机械判罚块（那是给检查脚本的数据，模型不看）和"来源"节（出处集中住在 [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md)，随组合出门是浪费上下文）。

互斥和路由为什么放在编译期？因为手管不住。这份 style.md 以前靠手写指针维护，指针列表和路由头各写各的，两处慢慢对不上。现在清单是唯一源头，成品是生成物，对不上这件事从结构上消失了。

## 为什么规则住 markdown，选择住 json

规则本体是散文加正反例，json 装不下。json 只干一件事：记你选了哪个档，这正是它擅长的。分工定了：md 是内容，json 是选择，bake 把两者合成一份成品。改口味永远是改清单里一个词再重跑。

## 想自己加层

层卡是什么、进门三问、禁收什么，全在 [recipes/README.md](../recipes/README.md)。钩子那套（长对话防漂移）是另一份：[anchoring.md](anchoring.md)。检查脚本见 [checks.md](checks.md)。
