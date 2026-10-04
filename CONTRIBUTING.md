# 贡献指南

这个仓库收三种贡献：一是新配方层，给已有维度加新档位、新开一个病灶层或场景层都算。二是改现有层的条款。三是 bad case，装了配方还是冒出来、该被某条拦住却没拦的病句。路都接好在各处的正主文件里，所以本文只给先后顺序，不重复正文。

## 加一层或改一层

1. 先读 [recipes/README.md](recipes/README.md)。进门三问（换个用户还成立吗、归哪层、有没有管辖声明）和层卡五项，过了才进门。
2. 动 base（clarity）要走 [checks/cases.md](checks/cases.md) 回归集，改完过一遍全部案例，治好的病不许放回来。
3. 你的层要带机械判罚数据的话，词表用"禁 | 改成"表格，正则住层文件的 lint 围栏块，引擎自动认，零代码改动。机制见 [documents/checks.md](documents/checks.md)。

## 跑检查

```bash
python3 -m unittest discover -s tests   # 单元测试
python3 checks/lint.py --self-test      # 判罚引擎自测
python3 checks/lint.py 你改的文件.md    # 词形判罚
```

## 改分发文档

README、INSTALL、PRESETS 这类分发文档，改完走三层才算过：配方自扫（anti-ai、natural-chinese、clarity 各扫一遍），干净上下文的子代理审展开（[checks/expansion-review.md](checks/expansion-review.md)），维护者过目。

## 报 bad case

开 issue 按模板填：病句原句、想要的样子、该拦没拦的是哪层哪条、出现的场景。收进来的 case 进回归集，同一教训复发满两次就毕业成条款。

## 边界

配方是大家共用的公共正本，个人口味写进去对别的用户不成立，所以不收。判死词表（build/bans.md）、语气校准（build/voice.md）、钩子策略（build/policy.json）这类只对你自己成立的东西，住各自的 build/，别提进公共区。
