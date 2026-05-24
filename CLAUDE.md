# CLAUDE.md

## Deployment Server

- Host: 8.152.2.222
- SSH user: root
- Domain: JSVOC.jadejinyuxuan.com

## Production OSS

- OSS bucket: `jsvoc2`
- OSS endpoint currently required by the bucket: `oss-cn-beijing.aliyuncs.com`
- OSS credentials live only in `/opt/JSVOC/current/.env` as `OSS_ACCESS_KEY_ID` and `OSS_ACCESS_KEY_SECRET`.
- Do not commit real AccessKey ID or AccessKey Secret values to Git. Keep only empty placeholders in `.env.example` and docs.
- The backend uses OSS for generated images, generated videos, and uploaded reference media. Required RAM permissions include object upload, download/signing support, and delete for verification/cleanup, for example `oss:PutObject`, `oss:GetObject`, and `oss:DeleteObject` on bucket `jsvoc2`.
- If the bucket is recreated or moved to another region, update `OSS_ENDPOINT` to the endpoint shown in the OSS console for that bucket before restarting `jsvoc_backend`.

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

---

## 1. 先想再写

**别瞎猜，不确定就问。**

动手之前：
- 先把你的假设说出来。拿不准的，直接问用户。
- 有多种理解方式时，列出来给用户选，别自己偷偷拍板。
- 如果有更简单的做法，说出来。该 push back 就 push back。
- 看不懂的地方，停下来，说清楚哪里不懂，然后问。

## 2. 简单优先

**能 50 行搞定的事，别写 200 行。**

- 用户没要的功能，不加。
- 只用一次的东西，别抽象成通用组件。
- 没要求的"灵活性""可配置性"，不做。
- 不可能出错的场景，别写错误处理。
- 写完之后问自己：" senior 工程师看了会说这过度设计吗？" 如果是，砍掉。

## 3. 外科手术式修改

**只动该动的地方，别顺手重构别人的代码。**

改代码时：
- 别"顺手优化"旁边的代码、注释、格式。
- 没坏的东西别重构。
- 哪怕你风格不同，也按项目现有的来。
- 看到无关的死代码？提一句，别删。

自己的改动产生了孤儿代码：
- 把你改出来的无用 import/变量/函数删掉。
- 但别碰之前就存在的死代码，除非用户让你删。

检验标准：每一行改动，都能追溯到用户的某个明确要求。

## 4. 目标驱动执行

**先定义什么叫"完成"，做完要验证。**

把模糊需求变成可验证的目标：
- "加校验" → "先写几个非法输入的测试，让它们跑通"
- "修 bug" → "先写一个能复现 bug 的测试，再修"
- "重构 X" → "重构前后测试都要过"

多步骤任务，先列个简单计划：
```
1. [步骤] → 验证：[检查点]
2. [步骤] → 验证：[检查点]
3. [步骤] → 验证：[检查点]
```

目标越清晰，你越能独立推进。目标模糊（"让它跑起来"），你就得不停问用户。

## 5. 模型只做判断

**路由、重试、解析这类确定性的活，别丢给 LLM。**

- 能写 `if/else` 或正则搞定的事，硬编码。
- LLM 只干它该干的：理解模糊输入、自然语言处理、创意生成。
- 别让模型决定"要不要重试""走哪条分支"——你自己写逻辑。

## 6. 硬 Token 预算

**防止调试无底洞。**

- 单次任务控制在 ~4K token。
- 整个会话控制在 ~30K token。
- 如果陷入死循环（一直修一直错），停下来换个思路，别硬烧 token。

## 7. 冲突选一边

**别混着来。**

- 项目用 snake_case，你就别引入 camelCase。
- 项目用 Options API，你就别乱用 Composition API。
- 状态本来是局部的，别为了一时方便上全局状态。
- 一致性 > 个人喜好。

## 8. 先读再写

**改之前，看看谁在调用它，它调用了谁。**

- 改函数前，先看调用方期望什么。
- 加新接口前，先看现有的路由和 schema 模式。
- 引入工具函数前，先读它的签名和行为。
- 别猜接口——去读源码。

## 9. 测试验证意图

**测的是"为什么这么做"，不是"做了什么"。**

- 测试过了但 guard 不住原始意图，等于白写。
- 问自己："如果有人回滚了我的修复，这个测试会挂吗？"
- 测试应该文档化需求，而不只是跑一遍代码。

## 10. 每步检查点

**做完一步，总结一下。**

每个关键步骤后：
- 做了什么？
- 验证了什么？（测试、构建、手动检查）
- 还剩什么？

防止默默跑偏，也让用户知道进度。

## 11. 遵循代码库惯例

**入乡随俗。**

- 命名、格式、架构，按项目现有的来。
- 别引入新的 lint 规则、新的目录结构、新的依赖模式——除非讨论过。
- 项目用 Element Plus，你就别突然引入 shadcn/ui。

## 12. 失败要大声

**别在不确定的时候写"完成"。**

- 任务只做完了一半，或者你跳过了某步，明确说出来。
- 你做了一个可能错的假设，标出来。
- 验证不了（比如测试跑不起来），说明情况，别假装成功。
- 暴露不确定性，让用户来决定。

---

## 设计风格 (Design Language)

项目前端统一遵循以下设计规范。所有新页面、新组件必须对齐这套语言，不引入偏离的风格。

| 维度 | 规范 |
|------|------|
| **颜色 (Color)** | Muted and postal, monochromatic. 低饱和邮政色调，单色系为主。灰蓝、灰绿、暖灰为基底，避免高饱和跳色。 |
| **排版 (Layout)** | Card based design with layered elements. 基于卡片的设计，带有分层元素。信息以卡片为单位组织，卡片之间有明确的层级和堆叠关系。 |
| **风格 (Style)** | Neo-minimalism. 新极简主义。元素克制、留白充分、边框纤细、无多余装饰。 |
| **设计哲学 (Philosophy)** | Approachable sophistication. 平易近人的高级感。视觉上精致但不疏离，专业但不冰冷。 |

**应用准则：**
- 主背景使用深色系（当前项目为 dark glass jade theme），但配色必须保持 muted / low-saturation。
- 卡片使用半透明毛玻璃（glassmorphism）或纯色分层，阴影 subtle 且统一。
- 交互元素（按钮、输入框）保持 minimal，hover 状态用透明度或微位移反馈，不用高亮描边。
- 字体层级清晰：大标题 bold、正文 regular、辅助信息 muted color + small size。
- 动画克制：150–300ms 微交互，ease-out 曲线，不喧宾夺主。

---

**这 12 条起作用的表现：** diff 里没那么多无关改动，少因为过度设计而返工，有问题先问而不是做错了再问。
