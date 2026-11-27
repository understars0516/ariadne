# Ariadne — 数据分析与研究工作室

> [English](README.md) | **中文**
>
> 本文是英文版 README 的中文翻译；若两者出现不一致，以 [英文版](README.md) 为准。

一套面向表格数据的完整、研究级分析能力：从"这个文件里有什么"，一直走到审稿人能接受
的报告；再从"接下来该问什么"，走到每一条都能追溯到证据的结论。

> **为什么叫 Ariadne？** 神话里，她给忒修斯一根线，引他走出迷宫。这里做的事情一样：数据是
> 迷宫，这个 skill 手里握着那根线——画像（profile）、提取（extract）、建模（model）、
> 提出想法（ideate）、制定计划（plan）、执行（execute）、下结论（conclude）——每个转角
> 都有一个关卡，线因此不会断。

前后两半：

- **阶段 A–F：分析。** 先做数据画像，再提取信息，然后在诊断把关下建模，最后输出报告：
  APA 表格与正文（F1）以及**出版级图表**（F2）。
- **阶段 G–K：研究闭环。** 生成有证据锚定的研究想法 → 用户选定一个 → 写出可执行的计划 →
  用户批准 → 实现并验证 → 下结论 → QA 与签署交付。

四道编号关卡把工作分开，每道拦一类失败：跑不动代码的环境、问错的问题、把正确的执行用在
错误的计划上、以及拿未经核实的工作下结论。第五道关卡在图离开之前审计它。

## 为什么需要它

常规分析擅长回答"被问到的那一问"，却总在同样几个地方盲：

1. **它只分析被问到的数据。** 它不会把整个关联族（family）都测一遍，于是只报告分析者恰好
   想到的那几个。
2. **它报告数字，却不报告假设违背的代价。** 正态性检验没过会被记一笔；它值多少没人量化，
   报告的标准误也不会因此改变。
3. **它在衔接处丢信息。** 搜索过程中发现的强关联，可能一路滑进结论，却从未被标明是探索性的。
4. **分析一结束它就停了。** 下一步做什么全凭分析者想象，计划是隐含的，结论写在"实际跑过什么"
   之上而无人核对。

这个 skill 补上这四个缺口：完整的 FDR 受控扫描、会改变报告内容的诊断、追踪每条发现状态的
发现台账、锚定在这些发现上的想法生成，以及一道不让结论跑在证据之前的计划/结论关卡。

## 一次请求长什么样

```
你：我有一份数据在 data/study.csv —— 我想用它做研究，但不知道该怎么分析。
```

skill 会先做数据画像、提取数据里真正有的信息、在诊断把关下建模，产出报告、发现台账和
可复现性清单。然后它给出下一个问题：

```
你：好了，分析做完了。我接下来该研究什么？
Agent：[用 13 个生成器扫过已有发现 → 6 个排序后的、有证据锚定的想法，
        每个都带这个样本量下的检验效能，以及什么结果会推翻它]
       I1 … I2 … I3 …  推荐 I1，理由是 …
       你想把哪一个做成计划？
你：I1
Agent：[可执行计划：估计目标、全局约束、审查重点、带已知答案校验的任务]
       —— 这份计划是否抓住了你想要的？
你：是
Agent：[按台账执行，并用已知答案校验逐步验证，关卡通过] →
       [结论：主张表格，每一行都引用一个产物文件]
```

## 安装

把它克隆（或直接复制文件夹）到你的 agent 会扫描的 skills 目录：

```bash
# 用户级（DeepSeek Harness profile），所有会话都可用
git clone https://github.com/understars0516/ariadne.git "$DSH_HOME/skills/ariadne"

# 项目级，只有在该项目里启动的会话可用
git clone https://github.com/understars0516/ariadne.git .dsh/skills/ariadne

# 机器上没有 git？直接复制文件夹
cp -r ariadne "$DSH_HOME/skills/"
```

这个 skill 就是一堆 Markdown、Python 和模板：不需要构建步骤，也不需要在 profile 里注册包。

然后在**使用之前**配置并验证 Python 环境：

```bash
python -m venv .venv && . .venv/Scripts/activate   # Windows:  .venv\Scripts\activate
python -m pip install -r requirements.txt          # pandas + numpy：分析所需的全部
python -m pip install -r requirements-optional.txt # 图表、.xlsx 导出与交叉校验
python scripts/check_env.py                        # 判定：READY / DEGRADED / BLOCKED
```

`check_env.py --fix` 会打印出缺什么、该跑哪条安装命令。
需要 Python 3.9+ 与 `pandas`、`numpy`；其余都是可选项，只影响渲染或交叉校验
（详见 `references/environment-setup.md`）。

## 预检：为什么先做环境检查

后面每一个阶段都假定：解释器能 import pandas/numpy、内置统计引擎算出的数字是对的、产物文件
能写出去。只要有一条不成立，失败会在很后面才浮现，而且看起来像分析出了 bug——图永远不出现、
导出静默写出空文件、`nan` 的 p 值被赖到数据头上。

所以阶段 0 是一道关卡，而且它验证的不止是 import：

| 检查项 | 它拦住的那类失败 |
|---|---|
| 解释器路径 + 版本 | 在错误的 Python 下做分析（`python` vs `python3` vs conda base） |
| pandas / numpy 可导入 | 三步之后每个脚本都失败 |
| **引擎自检——12 项对照解析解已知值** | 引擎能 import 但算错数 |
| 输出目录与临时目录可写 | 产物静默写不进去 |
| 控制台编码 | 非 ASCII 报告文本在 cp936 控制台上抛异常 |
| 能力摘要 | 到最后才发现图只是规格说明，不是图片 |

| 退出码 | 判定 | 应对 |
|---|---|---|
| 0 | READY | 继续 |
| 2 | DEGRADED | 继续，但要说明哪些输出被削弱 |
| 1 | BLOCKED | 停下修环境；绝不绕过 |

环境报告（`out/env.json`）会被折进可复现性清单，所以报告里始终记着解释器、包版本，以及引擎
自检是否通过。

## 快速开始

```bash
# --- 阶段 0：环境关卡 ---------------------------------------------------
python scripts/check_env.py --json out/env.json --report out/env.md

# --- 分析这一半 ---------------------------------------------------------
# 1. 这是什么数据？
python scripts/profile_data.py --input data.csv --out out/run --mechanism

# 2. 数据里有什么？（完整扫描，FDR 受控）
python scripts/info_scan.py --input data.csv --outcome post_score --group arm \
    --id-columns participant_id --out out/run

# 3. 在诊断把关下，什么能预测结果？
python scripts/model_fit.py --input data.csv --outcome post_score \
    --predictors adherence --covariates age,baseline_score --out out/run

# 4. 表格与正文
python scripts/apa_tables.py --input data.csv --from-json out/run_model.json --out out/report
python scripts/report_builder.py --artifacts out --outcome post_score \
    --research-question "..." --hypothesis "..." --out out/final

# 5. 出版级图表，然后审计它们
python scripts/figures.py --input data.csv --group arm --outcome post_score \
    --model-json out/run_model.json --journal nature --out out/figs
python scripts/check_figure.py out/figs --journal nature \
    --spec out/figs/figures.json --strict      # PASS / WARN / FAIL

# --- 研究闭环 -----------------------------------------------------------
# 6. 接下来该问什么？（排序、锚定证据、可行性已计算）
python scripts/get_ideas.py --input data.csv --artifacts out --outcome post_score \
    --goal explain --out out/ideas
#    → 展示 ideas.md，用户选定 I1

# 7. 把选定的想法变成一份用户能判断的计划
python scripts/plan_analysis.py new --ideas out/ideas.json --select I1 \
    --data data.csv --out analyses/equivalence/plan.md
#    → 用户审阅计划并批准

# 8. 执行（写分析代码、用已知答案验证、记台账）

# 9. 证明它确实被执行过，然后下结论
python scripts/plan_analysis.py gate --plan analyses/equivalence/plan.md \
    --artifacts analyses/equivalence/outputs
python scripts/plan_analysis.py conclude --plan analyses/equivalence/plan.md \
    --artifacts analyses/equivalence/outputs --out analyses/equivalence/conclusion.md
```

每个脚本都能独立运行，并向控制台打印 Markdown 报告；`--help` 列出全部选项。所有脚本都
接受 CSV、TSV、Parquet、Excel、JSON、Stata 和 SPSS 文件。


## 出版级图表

图表的问题很少出在绘图调用上。它是一个藏住了五个点分布的均值柱、一条凭空造出关系的双 y 轴、
一张存成 JPEG 的线稿，或者一张按 7 in 宽画好、再塞进 3.5 in 栏宽里、直到 8 pt 标签变成
4 pt 的图。所以这一步是*关卡*，不是便利：

```bash
python scripts/figures.py --input data.csv --group arm --outcome post_score \
    --model-json out/run_model.json --journal nature --out out/figs
python scripts/check_figure.py out/figs --journal nature --spec out/figs/figures.json --strict
```

| 要求 | 做法 |
|---|---|
| 精确的印刷尺寸 | 按 `figure_size(journal, span)` 绘制——Nature 单栏 3.50 / 1.5 栏 4.72 / 双栏 7.20 in |
| 矢量优先 | PDF + SVG + PNG；JPEG 会被拒绝并说明原因 |
| 色盲安全 | Okabe-Ito 调色板**外加**线型/标记的冗余编码，并导出一份灰度副本 |
| 分布可见 | 雨云图（半小提琴 + 箱线 + 抖动散点），每组印上 n |
| 字体嵌入 | `pdf.fonttype = 42`；审计在 Type 3 字体上直接失败 |
| 图注契约 | 必须写明 n 与不确定性的类型；逐图审计 |
| 期刊预设 | nature · science · ieee · elsevier · pnas · chinese · general |
| 中文排版 | `--lang zh --serif-zh` → 宋体 + Times New Roman，并修正负号 |

可生成的图：分布图、组间比较（雨云图）、散点 + 拟合 + 置信带、森林图、ROC、有序相关热图、
四联残差诊断、队列留存、带标注的拼合图。没有 matplotlib 时这一步仍会跑——它会写出一份精确
的图表规格说明，而不是失败。

## 目录内容

| 路径 | 是什么 |
|---|---|
| `SKILL.md` | 入口：原则、入口路由、阶段 A–K、方法选择表、研究闭环 |
| `references/` | 18 篇深度参考，按需加载 |
| `scripts/` | 13 个可运行工具 + 一套自包含的统计引擎 |
| `assets/` | 12 个模板：想法、执行计划、台账、结论、研究方案、报告、假设日志、发现台账、数据字典、QA 签署、稿件骨架 |
| `tests/` | 对照 scipy 的引擎校验、17 段冒烟测试、演示数据生成器 |
| `examples/` | 演示数据集上的真实输出 |
| `evals/` | 14 条带断言的测试提示词，用于"有 skill / 无 skill"对照 |

### 参考文档

| 文件 | 回答什么 |
|---|---|
| `environment-setup.md` | 用哪个解释器、装哪些包、卡住的环境怎么修 |
| `profiling-and-quality.md` | 数据是什么，哪里会出问题 |
| `information-extraction-ladder.md` | 把信息榨出来的九级阶梯 |
| `methods-index.md` | 该用哪个方法，它要什么假设、有哪些变体、怎么报告 |
| `modeling-and-diagnostics.md` | 每条假设、它的检验、它的补救，以及补救的代价 |
| `study-design-and-power.md` | 设计、估计目标、样本量、预注册 |
| `causal-inference.md` | 什么时候可以说"效应"；DAG、PSM、DiD、IV |
| `longitudinal-multilevel-survival.md` | 重复测量、嵌套、增长、生存 |
| `psychometrics.md` | 量表、信度、效度、EFA/CFA、一致性、ROC |
| `multivariate-and-segmentation.md` | PCA/EFA、聚类、分群验证 |
| `business-analytics.md` | 指标、队列、漏斗、A/B 实验、根因分析、预测 |
| `statistical-reporting-apa.md` | 表 1–12、p 值格式、结果段落 |
| **`publication-figures.md`** | 图形选择、18 个陷阱、期刊规格、图注契约、三层自检 |
| `visualization-and-narrative.md` | 图形选择、设计、叙事、执行摘要 |
| `documentation-and-qa.md` | 假设日志、数据目录、QA 关卡、同行评审 |
| **`ideation-get-ideas.md`** | 13 个想法生成器、质量标准、排序、如何呈现想法 |
| **`plan-and-execute.md`** | 计划格式、已知答案校验、台账与裁定、结论 |
| `software-recipes.md` | 各方法族的 Python 与 R 代码 |

## 验证

两套测试，都随仓库发布、可直接运行：

```bash
# 统计引擎与 scipy/statsmodels 对齐（约 120 项检查）
python tests/validate_against_scipy.py

# 整条流水线在"故意埋了问题"的数据上仍然工作
python tests/smoke_test.py
```

冒烟测试会生成一份数据集，里面埋着哨兵值、MCAR 与 MAR 缺失、重复行、常数列、ID 列、
大小写不一致的类别、派生变量、嵌套的聚类结构，以及一个重偏态的结局变量——然后断言：画像器
把它们逐个找出来、干净列*不会*被误报、FDR 存活项不超过原始显著项、检测到异方差时模型切换到
稳健标准误、样本量计算对上 G*Power 的参考值、报告包含每一个必需章节、**绝不把派生得分当作
它自身结局的预测变量**、生成的计划带有已知答案校验与审查重点、**关卡拦住未执行的计划并放行
已完成的计划**，以及结论里的主张确实引用了真实产物。

它还断言那些"说起来容易、证起来难"的部分：导出的图在容差内符合期刊栏宽；JPEG 和没有 DPI 的
PNG 都会被审计判 FAIL；缺少 n 的图注会 WARN；没有 matplotlib 时图退化为规格说明；坏掉的解释器
会给出退出码 1（BLOCKED），而不是一份兴高采烈的报告。

`tests/validate_against_scipy.py` 需要 `scipy`（回归部分还需 `statsmodels`）；
`tests/smoke_test.py` 只需要 `pandas` 和 `numpy`。

## 设计原则

**方法跟着数据走，不跟着偏好走。** 先做画像；数据的测量尺度和形态决定方法族。请求决定你
要回答什么，而不是怎么回答。

**搜索必须声明并校正。** 每个被测过的配对都要报告，并声明它的多重比较族（family），在族内做
Benjamini-Hochberg FDR。原始显著与校正后显著之间的落差本身也要报告，因为那正是搜索的代价。

**诊断会改变输出。** 如果 Breusch-Pagan 或 RESET 没过，报告的标准误就要变，而且报告要写明
这一点。诊断不是附录。

**确认性与探索性始终分开。** 发现台账给每条发现一个状态，报告把两者显眼地分开。

**零结果自带信息。** 每个零结果都连同它的区间和最小可检测效应一起报告，于是"我们什么都没
发现"变成"小于某个尺度的效应我们检测不到"。

**想法来自发现。** 每个提出的后续问题都要引用促成它的扫描行或台账条目，并附带计算出来的
可行性。说不出自己证据的想法只是愿望。

**不越过已核实的东西去主张。** 被批准的想法、被批准的计划、以及通过的证据关卡，横在数据与
结论之间。

## 设计决策及其理由

| 决策 | 为什么这样 |
|---|---|
| 逐阶段设关卡，而不是先按复杂度分档 | 复杂度分档无法告诉你假设是否成立；关卡可以 |
| 一个路由器（`SKILL.md`）加 18 篇参考，而不是每个能力一篇文档 | 渐进披露：agent 只加载它需要的那两页，而不是全部 |
| 扫描报告每一个检验，而不只是被请求的那一个 | 只报告被请求的检验，会把产生它的那场搜索藏起来 |
| 诊断失败要明说并改标准误，而不是悄悄换方法 | 悄悄换方法看起来像本事，实际不可复现 |
| 没有 matplotlib 时，图退化为书面规格 | 精简环境应该拿走图，而不是拿走分析 |
| 想法关卡与计划关卡是拦截，不是提示 | 用户没有选择的问题，是他们不会用到的活儿 |
| 计划从已批准的想法生成，而不是手写 | 约束是被复制过去的，不是被记住的；稳健性检验集不会悄悄缩水 |
| 结论关卡由机器检查（`plan_analysis.py gate`） | 写在未完成工作之上的结论是虚构，无论读起来多好 |
| 图表审计是可执行的（`check_figure.py`） | "屏幕上看着挺好"不是期刊接受的标准 |
| 不做交互式或纯 notebook 图 | 交付物是可印刷的投稿材料；HTML 活不过期刊工作流 |

## 可移植性

推断代码都在 `scripts/_dsp_stats.py` 里——纯 numpy、不依赖 scipy——所以只装了 pandas 的机器
也能跑。它实现了各种分布、检验、带稳健标准误的 OLS/logistic、PCA、聚类、信度、ROC、生存、
功效与 bootstrap，并且已对照 scipy/statsmodels 验证。没有 matplotlib 时，`figures.py` 会输出
一份精确的图表规格说明，而不是失败。

## 许可证

MIT —— 见 [LICENSE](LICENSE)。

本 skill 的正文、脚本、模板和示例都是为此编写的。当某项技术有经典出处时，参考文档只点出
该方法的名称而不复制原文（Benjamini-Hochberg FDR、Okabe-Ito 调色板、APA 7 报告规范、标准
诊断流程），读者可以据此回溯到原始文献。