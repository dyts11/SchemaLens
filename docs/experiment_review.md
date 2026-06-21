# Paper 实验完整性评估与补充建议

**Paper**: Disentangling Structure and Semantics: How Schema Representation Affects LLM-Based SQL Generation
**日期**: 2026-05-25
**当前状态**: 6×3 factorial 已跑完 9 个模型 × 18 conditions × 397 questions

---

## TL;DR

| 问题 | 结论 |
|------|------|
| 是否要做 Qwen-14B 的 prompt tuning (PEFT) 对比？ | **不建议** — 偏离主线；留作 follow-up |
| 是否要做 Qwen-14B 的 prompting 策略对比？ | **建议做 few-shot / CoT / SC 中的一两个** |
| 当前实验最大缺口？ | (1) 第二个 benchmark (2) error breakdown n=1 (3) 无显著性检验 |

---

## 1. 关于 "Qwen-14B 不同 prompt tuning 方式对比"

### 结论：不建议作为主线实验

Paper 的核心 contribution 是 *prompt-based zero-shot 设置下 schema representation 的因果分析*（controlled factorial study）。如果引入参数微调（LoRA / Prefix Tuning / Prompt Tuning 等）：

- 范围发散，审稿人会问 "那为什么不直接 fine-tune？"
- 削弱 "prompt representation matters" 的清晰主张
- 增加大量算力 + 工程成本，对核心结论增益有限

### 但是这几个 *prompting 策略对比* 值得在 Qwen-14B 上补

| 策略 | 实验设计 | 价值 | 优先级 |
|------|---------|------|--------|
| **Few-shot ICL** (k=1,3,5) | 在 L6·S1 加 in-context examples | 直接测试 "语义缺失能否靠 ICL 补救"；若不能 → 强化核心 claim | 🔴 高 |
| **CoT prompting** | L4–L6 × S1，要求模型先 reason | 看推理是否能 "激活" 结构 metadata | 🟡 中 |
| **Self-consistency** (n=5) | S1 全列 majority vote | 测试随机性是否就是问题 | 🟢 低 |

---

## 2. 应该补的主要实验（按 ROI 排序）

### 🔴 必须补（直接影响审稿通过率）

#### 2.1 第二个 benchmark 验证 generalization

- **现状**：Limitation 第一条已自爆 "evaluated on a single benchmark family"
- **建议**：至少做 Spider-dev 子集（200–300 题）
- **范围**：
  - 不需要做 1NF/2NF（Spider 多为简单 schema，找 1–2 个能 materialize 的即可）
  - 主体只跑 **L3–L6 × S1–S3** = 12 conditions，验证 asymmetric substitution 复现
- **模型**：Qwen-14B + Gemini 2.5 Flash 两个就够
- **预算**：~6–8 小时
- **风险**：不补这一条，"generalization" 会直接被拒

#### 2.2 Qwen-14B 的 error breakdown（Table 5 扩展）

- **现状**：Table 5 只有 Gemini 2.5 Flash，n=1 model
- **建议**：在 Qwen-14B 上跑同样的 5 类错误分类
- **可复用**：已有的 CSV 结果 + Claude Sonnet 4.5 分类 pipeline
- **预算**：~2 小时
- **价值**：让 "structure redistributes errors" 的 claim 不再单点支持

#### 2.3 统计显著性

- **现状**：只有 bootstrap CI
- **建议**：mixed-effects regression
  ```
  EX ~ L + S + L×S + (1|db) + (1|question) + (1|model)
  ```
- **报告**：L×S 交互项的 p-value 和 effect size → 直接量化 "非对称"
- **预算**：~1 天（建模 + 写作）
- **价值**：从 "我们观察到" 升级为 "我们统计上证明了"

---

### 🟡 强烈建议补

#### 2.4 In-context 干预实验 — 直接测试 "lexical anchor" 假设

- **设计**：在 S1 prompt 里**显式提供 S3→S1 mapping 字典**作为附加上下文
- **预期结果**：
  - 若 EX ↑ 至接近 S3 水平 → 强证据：模型缺的就是 lexical anchor
  - 若 EX 不升 → 说明 grounding 之外还有问题，需调整 claim
- **范围**：Qwen-14B × 3 个 db × S1 全列
- **预算**：~1–2 小时
- **价值**：**最强的因果证据**，直接支撑 paper 标题里的 "Disentangling"

#### 2.5 Sample rows 消融（回应 production 实践）

- **设计**：在 L3·S1 加 3 行样例数据，看能否替代 semantic naming
- **价值**：直接回应 reviewer "为什么不像 DAIL-SQL / production 那样加 sample rows？"
- **预算**：~1 小时

#### 2.6 Schema width 的回归量化

- **现状**：Fig 4 已观察到 schema width 主导，但只用 narrow/balanced/wide 三分
- **建议**：连续变量回归
  ```
  pooled_acc ~ avg_cols + n_tables + struct_choice + sem_choice
  ```
- **报告**：每个变量的标准化系数 + R²
- **价值**：比离散三分组更有说服力

---

### 🟢 加分项（时间充裕再做）

#### 2.7 Reasoning model 对比

- 至少跑 DeepSeek-R1 / Claude Sonnet 4.5 thinking / GPT-5 中一个
- 关键对比：L1·S3 vs L6·S1 一对，看 reasoning 能否激活结构 metadata
- **价值**：回应 "是不是 reasoning 模型就不一样了"

#### 2.8 L1/L2 ground-truth 校准

- 在 1 个 db 上手写 ~50 题的 1NF gold SQL
- 量化 "L1/L2 是 lower bound" 到底偏低多少 pp
- **价值**：把 Limitation 第二条从 "无法量化" 升级为 "已量化在 X pp 以内"

#### 2.9 Cross-model substitution gap 全表

- 现在 Fig 3 只有 4 模型条形图
- 扩成 9 模型 × 9 db 的完整 heatmap
- **价值**：让 "robust across models" 的 claim 一图说清

---

## 3. 推荐的最小完成路径

如果时间紧（< 2 周），**只补这三个就能大幅提升投稿质量**：

1. ✅ **Spider 子集复现 asymmetric substitution**（Qwen-14B + Gemini，~6 小时跑完）
   → 让 generalization 站得住
2. ✅ **Qwen-14B 的 error breakdown**（复用现有 csv，~2 小时跑 Claude 分类）
   → 让 error 分析不再 n=1 model
3. ✅ **显式 mapping 注入实验**（1 模型 × 3 db × S1，~1 小时）
   → 给最强的因果证据

总预算：**~10 小时**，可在 2 天内跑完。

---

## 4. 不建议在这一篇做的事

| 项目 | 为什么不做 |
|------|-----------|
| LoRA / Prefix Tuning 等 PEFT 对比 | 偏离 prompt-based 主线，留 follow-up |
| 自研 text-to-SQL 系统对比 | 这是 analysis paper 不是 system paper |
| 加更多模型（>10 个） | 边际收益低，scaling 已用 Qwen ladder 说清 |
| 跑全量 BIRD（>1000 题） | 已用 397 corrected subset，扩量收益不大 |
| 加 chain-of-table / decomposition 等 SOTA pipeline | 同样偏离 controlled study 设计 |

---

## 5. 写作层面的小建议

- **Abstract 第 26 行**："negligible below 3B" → 建议改成 "emerges at ≥3B for structural, ≥7B for semantic"，更精确
- **§5.1 Fig 1 caption**："across four models" 但图里只有一个 Qwen-14B 的 heatmap，需要核对
- **§5.3 Table 6**：(d), (e) 在正文引用但表里只有 (a)(b)(c)，需补全
- **Limitations 可以多写一条**：所有模型都是 instruction-tuned，没测 base model，是否 instruction tuning 本身放大了 semantic 依赖？
