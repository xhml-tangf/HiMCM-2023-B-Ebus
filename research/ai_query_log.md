# AI query and artifact log

This is the private project's working record for the competition AI disclosure.
It contains user-request text and the resulting artifacts, but no API key or
private authentication material. The final paper identifies the tools and points
to this log; model reasoning traces are not research outputs.

## Tool identity

- OpenAI Codex, GPT-6: planning, source research, mathematical modelling, code
  implementation, numerical checks and LaTeX composition.
- DeepSeek Flash through the configured Codex route: continuation work on GTFS
  recovery, audits, scenario implementation and manuscript integration.

The 2023 HiMCM source problem was supplied locally. No original 2023 solution
paper was requested or used. Other-year HiMCM examples and the official rules
were used only as format and research-quality references.

## Request 1: research plan and model design

Working request (Chinese original):

> 现在，你的任务是先给这个题目做一个计划，来完成这一篇数学建模论文。使用先计划，先不用做稿子。这个题目我现在对它的理解大概是这样，相当于是有两个评分函数，一个是经济方面的，一个是环境方面的。然后后面两个问题都是前面定好方案之后后面执行。然后这两个评分函数负责评价一个公交车新车队的构造。那在这个过程中，我们就有很多输入的参数，包括公交车车型等等等等。然后完了以后，你再用这两个评分函数去评分，随后用这样一个方式去找到一个最大值。我大概的感觉是这个。关键是你要找一个数据比较好找的城市，这个找一个即可，后面两个问题才需要加上第二第三个。先做计划，找一下数据可用性，然后给一个大致的大纲和思路，然后我们进行下一步。

> 找一个备选，找一个备选的国家，最好是一个特定城市，大城市什么的，防止推进到一半，这个又不好跑。选两个吧，就是一共选三个不同的城市，但是我们在构造的时候先用温哥华来构造，这样温哥华如果数据各种方面出现问题，我们再转。然后现在可以开始上网搜索论文了。第一阶段，搜索关于公交车队转型的这些论文，包括电动公交车的研究、电动公交车路线规划、传统的规划以及新的基础设施的规划，这种城市规划类型的论文，以及相关的数学建模，但是唯一的限制是不能搜索当年HIMCM的原版文章。那在这个基础上，搜寻了一批论文之后，重点观察里面在用了什么数学模型，或者引用哪些数据来源，这时候再从这个方面搜索这些数学模型的研究和扩展，以及数据来源等等。现在做一波前期的研究。

Outputs: the research boundary, three-city design, source ledger,
`research/literature_and_transfer.md`, model equations, and the execution plan
recorded in the repository.

## Request 2: LaTeX, format and CPU experiments

Working request (Chinese original):

> 你用 LATeX，然后参考去年HIMCM的最高级别奖项的论文做格式参考，格式先规范好，避免后续再越改越错。

> 然后接下来用我电脑算力，现在只能用CPU哈，然后去跑一下算法，把具体的分数跑出来，可以调用尽可能多的算力，保证效果优先。

Outputs: `paper/ebus_transition.tex`, the compiled PDF, format and PDF QA
scripts, GTFS and block audits, charging LPs, the London MILP, the 432,768-case
assumption grid, scenario tables and figures.

## Request 3: fill missing evidence

Working request (Chinese original):

> 那个，你自己把这些基础问题解决好不好？然后把所有的数据尽可能填上，现在就是反复的工作阶段，把你漏掉的、不确定的东西全部补齐。

Outputs: deck/shuttle technical audit, regional economic and NOx/PM audit,
full-class cost boundary, APTA accessibility audit, updated parameter ledger,
and the final manuscript.

## Request 4: repository delivery

The private repository destination was authorized as
`xhml-tangf/HiMCM-2023-B-Ebus`. Local Git history is authoritative when the
network or approval service is unavailable; a remote upload is never described
as complete unless it is verified.

## Verification boundary

All numerical claims in the paper identify a source, method or result file.
Missing data are returned as `UNVERIFIED`, not estimated into zero. The human
team remains responsible for checking citations, the official team number and
the competition submission.
