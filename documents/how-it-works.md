# 机制：样式如何组合（从 combo.json 到 style.md）

## 三层模型

你挑的每一份层，都归在下面三层之一，层与层各管各的：

- **基座**（recipes/base/clarity.md）：必装。说清楚的通则，加整个组合的宪法（优先级、同维互斥、"可以"不是配额、判断法优先于词表）。
- **公共样式层**（recipes/flaws、tones、scenes）：病灶层挑着装，腔调层每个维度选一个档位，场景层按活挑。
- **个人校准层**（build/，整目录 gitignore）：判死词表 bans.md、语气校准 voice.md、人格卡 personas/（狐娘这类，一卡一文件）。换人用，整份换。

一条规则住哪层，你拿这句判别法问它：换个用户还成立，进公共层。不成立，进 build/。

## 选层清单 combo.json

你要维护的只有 build/combo.json 这份清单：

```json
{
  "flaws": ["anti-ai", "natural-chinese"],
  "persona": "fox-girl",
  "tones": { "rhythm": "mixed", "particles": "follow" },
  "scenes": ["artifacts"],
  "personal": ["bans", "voice"]
}
```

- flaws：装哪些病灶层，写文件名。
- persona：人格卡名（不带 .md），从 build/personas/ 取。单值键，一次只穿一套，写成列表 bake 直接报错。不写就是素人格。
- tones：腔调各维度选哪个档。维度是文件名前半（rhythm、density 这些），档位是后半（mixed、full 这些）。你想加新档，写个新文件就行，不用登记，编译器扫描目录自动认。
- scenes：场景层。示例里的 artifacts 是工件场景，管 commit、README、发布说明这类落地文件。
- personal：个人层文件名（不带 .md），从 build/ 取。

基座不用你选，永远在。

## bake.py 做什么

你在仓库根目录跑 `python3 tools/bake.py`，它把清单编译成 build/style.md。加 `--check` 就只校验，不写文件。

编译期拦三类错：选了不存在的文件、未知的维度或档位名、人格键写成列表或对象，任何一类都直接报错。腔调层每维一键一档：你想在一个维度下同时穿两份，就把档位值硬写成列表，bake 的档位校验当错误拦下，归在未知的档位名那一类。人格键也一样靠校验拦：json 允许把 persona 写成列表或对象，想同时穿两套人格就这么写，写进去了由编译期报错拦下。哪个维度没选，bake 提示没意见，合法。

bake 出来的 style.md 分两部分。开头一行路由头，从各层标题现场拼装，写明冲突时谁赢（我当场说的话 > 宿主项目规则 > 这套配方）。后面是全部选中层的全文。有两样东西编译时剔掉，你在这份文件里找不到：各层的机械判罚块（那是给检查脚本的数据，模型不看）和"来源"节（出处集中住在 [ACKNOWLEDGMENTS.md][ack]，随组合出门是浪费上下文）。

互斥和路由为什么放在编译期？因为靠手维护管不住。这份 style.md 以前靠手写指针维护，指针列表和路由头各写各的，两处慢慢对不上。现在我们把 combo.json 定成唯一源头，style.md 只是它的生成物，两处内容都从同一份清单生成，对不上这件事从结构上消失了。

## 为什么规则住 markdown，选择住 json

规则本体是散文加正反例，json 的键值结构装不下这种内容，所以规则住在 markdown。json 只干一件事：记你选了哪个档，这正是它擅长的。分工定了：md 是内容，json 是选择，bake 把两者合成一份成品。你改口味，永远是改清单里一个词再重跑。

## 想自己加层

你想自己加层的话，层卡是什么、进门三问、禁收什么，全在 [recipes/README.md][recipes]。长对话防漂移的钩子是另一份：[anchoring.md][anchoring]。检查脚本见 [checks.md][checks]。

[ack]: ACKNOWLEDGMENTS.md
[recipes]: ../recipes/README.md
[anchoring]: anchoring.md
[checks]: checks.md
