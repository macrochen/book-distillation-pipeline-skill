---
name: book-distillation-pipeline-skill
description: 书籍蒸馏→Custom GPT/Gemini Gem封装的自动化流水线。支持单本/多本/系列书籍（PDF/MD/TXT/EPUB），将非虚构书籍转化为AI智能体的"认知程序+知识库"，半自动部署到Gemini Gem或ChatGPT GPTs。
---

# 书籍蒸馏 Pipeline

本技能是书籍蒸馏任务的总控状态机。每一步产出物为固定MD文件，串联生成节点与检查节点。

使用这个技能时，先对用户说：

`正在使用 book-distillation-pipeline-skill，这是一个逐步确认的书籍蒸馏→智能体封装流程。`

## 核心等式

```
蒸馏产出物 = 认知程序（进Instructions）
归档材料 = 事实弹药（进Knowledge Base）
两者关系 = 引擎与燃料，非重复建设
```

**执行顺序（强制）**：先运行阶段2-A（指令），再运行阶段2-B（知识库）。先建立认知框架，再按图索骥提取事实。

## Hard Stops

- 未完成书籍分类就生成指令
- 未提取作者原声就生成指令
- 指令未通过审核就生成知识库
- 知识库未与指令交叉验证就打包
- 未询问目标平台（Gemini/ChatGPT）就执行打包
- 跳过用户审核checkpoints

## Project Layout

所有项目都在独立目录中运行：

`outputs/book-distillation-pipeline-skill/<yyyymmdd-slug>/`

基础必需文件：

- `00-book-info.md` - 书籍基本信息
- `01-classification.md` - 分类结果
- `02-author-voice.md` - 作者原声提取
- `03-instructions.md` - 最终指令（认知程序）
- `04-knowledge-base.md` - 知识库（事实弹药）
- `05-cross-validation.md` - 交叉验证报告
- `06-package-config.md` - 打包配置（名称、说明、指令摘要）
- `.pipeline-state.json` - 状态文件

## Stage Order

状态机顺序固定如下（每个step调用对应子skill）：

1. `step_0_init` — 初始化项目
2. `checkpoint_0_book_info` — 确认书籍信息
3. `step_1_classify` → **`book-classifier-skill`** — 书籍分类
4. `checkpoint_1_classify_review` — 分类审核
5. `step_2_author_voice` → **`author-voice-extractor-skill`** — 作者原声提取
6. `checkpoint_2_voice_review` — 原声审核
7. `step_3_instructions` → **`instruction-generator-skill`** — 指令生成
8. `checkpoint_3_instructions_review` — 指令审核
9. `step_4_knowledge_base` → **`knowledge-base-builder-skill`** — 知识库构建
10. `checkpoint_4_kb_review` — 知识库审核
11. `step_5_cross_validate` → **`cross-validator-skill`** — 交叉验证
12. `checkpoint_5_validate_review` — 验证审核
13. `step_6_package` → **`agent-packager-skill`** — 打包配置
14. `checkpoint_6_package_review` — 打包审核
15. `step_7_deploy` — 半自动部署

## Required Command Protocol

### Step 0: Init

支持的文件格式：PDF、MD、Markdown、TXT、EPUB

**单本书籍**：

```bash
python3 ${SKILL_DIR}/scripts/pipeline.py init \
  --project-dir "outputs/book-distillation-pipeline-skill/<yyyymmdd-slug>" \
  --book-path "<path-to-book>" \
  --title "<project-title>" \
  --author "<author-name>"
```

**同一作者多本书**（如张新民财报分析系列）：

```bash
python3 ${SKILL_DIR}/scripts/pipeline.py init \
  --project-dir "outputs/book-distillation-pipeline-skill/<yyyymmdd-slug>" \
  --book-path "财报基础.pdf" "财报进阶.md" "案例集.txt" \
  --book-title "财报分析(基础篇)" "财报分析(进阶篇)" "财报分析(案例篇)" \
  --title "张新民财报分析体系" \
  --author "张新民" \
  --project-type multi-book
```

**同一人物多来源**（如段永平投资系列：访谈录、博客、问答）：

```bash
python3 ${SKILL_DIR}/scripts/pipeline.py init \
  --project-dir "outputs/book-distillation-pipeline-skill/<yyyymmdd-slug>" \
  --book-path "访谈录.pdf" "博客精选.md" "雪球问答.txt" \
  --book-title "段永平访谈录" "段永平博客" "雪球问答录" \
  --title "段永平投资智慧" \
  --author "段永平" \
  --project-type person-series
```

**自动模式**（所有checkpoint使用默认值）：

```bash
python3 ${SKILL_DIR}/scripts/pipeline.py init \
  --project-dir "outputs/book-distillation-pipeline-skill/<yyyymmdd-slug>" \
  --book-path "<path(s)>" \
  --title "<title>" \
  --author "<author>" \
  --auto
```

**项目类型**（`--project-type`，可选，多书时自动检测为 multi-book）：
- `single`：单本书籍
- `multi-book`：同一作者的系列书籍
- `person-series`：关于同一人物的多来源材料（访谈、博客、问答等）

之后每次行动前先看状态：

```bash
python3 ${SKILL_DIR}/scripts/pipeline.py status \
  --project-dir "outputs/book-distillation-pipeline-skill/<yyyymmdd-slug>"
```

查看当前阶段说明：

```bash
python3 ${SKILL_DIR}/scripts/pipeline.py stage-brief \
  --project-dir "outputs/book-distillation-pipeline-skill/<yyyymmdd-slug>"
```

### Checkpoint 0: Book Info

收集书籍基本信息，写入 `00-book-info.md`。内容包括：
- 书名、作者、出版年份
- 用户提供的PDF路径
- 用户希望的目标平台（gemini/chatgpt，默认gemini）
- 用户的Gemini Gem创建页面URL（可选，默认 https://gemini.google.com/gems/create）

```bash
python3 ${SKILL_DIR}/scripts/pipeline.py approve \
  --project-dir "outputs/book-distillation-pipeline-skill/<yyyymmdd-slug>" \
  --stage checkpoint_0_book_info \
  --value confirmed
```

### Step 1: Classify

根据决策树确定书籍主类型和辅模块。使用 `templates/classification-guide.md` 中的决策树。

输出 `01-classification.md`，包含：
- 主类型（六选一）
- 辅模块（0-2个）
- 选择理由

```bash
python3 ${SKILL_DIR}/scripts/pipeline.py complete-action \
  --project-dir "outputs/book-distillation-pipeline-skill/<yyyymmdd-slug>" \
  --stage step_1_classify \
  --artifact classification_md="outputs/book-distillation-pipeline-skill/<yyyymmdd-slug>/01-classification.md"
```

### Checkpoint 1: Classify Review

展示分类结果，等待用户确认或修正。用户可调整主类型或辅模块。

```bash
python3 ${SKILL_DIR}/scripts/pipeline.py approve \
  --project-dir "outputs/book-distillation-pipeline-skill/<yyyymmdd-slug>" \
  --stage checkpoint_1_classify_review
```

### Step 2: Author Voice

从书中提取作者原声特征。使用 `templates/author-voice-prompt.md`。

输出 `02-author-voice.md`，包含：
- 口头禅、反问句式、比喻习惯、否定句式、数据引用习惯
- 每项附原文摘录和出现位置

```bash
python3 ${SKILL_DIR}/scripts/pipeline.py complete-action \
  --project-dir "outputs/book-distillation-pipeline-skill/<yyyymmdd-slug>" \
  --stage step_2_author_voice \
  --artifact voice_md="outputs/book-distillation-pipeline-skill/<yyyymmdd-slug>/02-author-voice.md"
```

### Checkpoint 2: Voice Review

展示作者原声提取结果，用户可补充或修正。

```bash
python3 ${SKILL_DIR}/scripts/pipeline.py approve \
  --project-dir "outputs/book-distillation-pipeline-skill/<yyyymmdd-slug>" \
  --stage checkpoint_2_voice_review
```

### Step 3: Instructions

根据分类结果选择对应模板（A-E），结合作者原声，生成指令。

使用：
- `templates/common-header-protocol.md` - 通用头部协议
- `templates/instructions-template-{A/B/C/D/E}.md` - 对应类型的指令模板

输出 `03-instructions.md`。

```bash
python3 ${SKILL_DIR}/scripts/pipeline.py complete-action \
  --project-dir "outputs/book-distillation-pipeline-skill/<yyyymmdd-slug>" \
  --stage step_3_instructions \
  --artifact instructions_md="outputs/book-distillation-pipeline-skill/<yyyymmdd-slug>/03-instructions.md"
```

### Checkpoint 3: Instructions Review

展示指令全文或关键片段。用户按审核清单检查：
- 可执行性（每条规则能写成"如果...那么..."）
- 语义触发（每个模型有状态/意图描述）
- 关键词覆盖（每个模型≥5个关键词）
- 冲突表（至少2条默认vs例外）
- 边界条件
- 作者原声出处

```bash
python3 ${SKILL_DIR}/scripts/pipeline.py approve \
  --project-dir "outputs/book-distillation-pipeline-skill/<yyyymmdd-slug>" \
  --stage checkpoint_3_instructions_review
```

### Step 4: Knowledge Base

根据分类结果选择对应知识库模板，结合指令中的模型，生成知识库。

使用 `templates/knowledge-base-template-{A/B/C/D/E}.md`。

输出 `04-knowledge-base.md`。

```bash
python3 ${SKILL_DIR}/scripts/pipeline.py complete-action \
  --project-dir "outputs/book-distillation-pipeline-skill/<yyyymmdd-slug>" \
  --stage step_4_knowledge_base \
  --artifact kb_md="outputs/book-distillation-pipeline-skill/<yyyymmdd-slug>/04-knowledge-base.md"
```

### Checkpoint 4: KB Review

展示知识库条目数量和关键条目预览。

```bash
python3 ${SKILL_DIR}/scripts/pipeline.py approve \
  --project-dir "outputs/book-distillation-pipeline-skill/<yyyymmdd-slug>" \
  --stage checkpoint_4_kb_review
```

### Step 5: Cross Validate

交叉验证指令和知识库的一致性：
- Instructions中的标志性提问在Knowledge中有对应条目
- Instructions中的每个模型名称在Knowledge中有定义
- Instructions冲突表中的规则在Knowledge中有详细解释

输出 `05-cross-validation.md`。

```bash
python3 ${SKILL_DIR}/scripts/pipeline.py complete-action \
  --project-dir "outputs/book-distillation-pipeline-skill/<yyyymmdd-slug>" \
  --stage step_5_cross_validate \
  --artifact validation_md="outputs/book-distillation-pipeline-skill/<yyyymmdd-slug>/05-cross-validation.md"
```

### Checkpoint 5: Validate Review

展示验证结果。如有缺失项，返回对应步骤补充。

```bash
python3 ${SKILL_DIR}/scripts/pipeline.py approve \
  --project-dir "outputs/book-distillation-pipeline-skill/<yyyymmdd-slug>" \
  --stage checkpoint_5_validate_review
```

### Step 6: Package

生成打包配置：
- 智能体名称
- 说明（Description）
- 指令摘要
- Conversation Starters（3个）
- 安全免责声明

输出 `06-package-config.md`。

```bash
python3 ${SKILL_DIR}/scripts/pipeline.py complete-action \
  --project-dir "outputs/book-distillation-pipeline-skill/<yyyymmdd-slug>" \
  --stage step_6_package \
  --artifact package_md="outputs/book-distillation-pipeline-skill/<yyyymmdd-slug>/06-package-config.md"
```

### Checkpoint 6: Package Review

展示打包配置，用户可修改名称、说明等。

```bash
python3 ${SKILL_DIR}/scripts/pipeline.py approve \
  --project-dir "outputs/book-distillation-pipeline-skill/<yyyymmdd-slug>" \
  --stage checkpoint_6_package_review
```

### Step 7: Deploy

半自动部署流程：

**Gemini Gem（默认）**：
1. 自动打开创建页面URL（可配置）
2. 自动复制名称到剪贴板
3. 自动复制说明到剪贴板
4. 自动复制指令到剪贴板
5. 用户手动上传知识库MD文件
6. 用户手动保存

**ChatGPT GPTs**：
1. 自动打开 https://chatgpt.com/gpts/editor
2. 同样半自动复制配置

```bash
python3 ${SKILL_DIR}/scripts/pipeline.py complete-action \
  --project-dir "outputs/book-distillation-pipeline-skill/<yyyymmdd-slug>" \
  --stage step_7_deploy \
  --meta platform=gemini \
  --meta deploy_status=completed
```

## Auto Mode

使用 `--auto` 参数时，所有checkpoint自动批准，使用默认选项：

| Checkpoint | 默认值 |
|------------|--------|
| checkpoint_0_book_info | confirmed |
| checkpoint_1_classify_review | approved |
| checkpoint_2_voice_review | approved |
| checkpoint_3_instructions_review | approved |
| checkpoint_4_kb_review | approved |
| checkpoint_5_validate_review | approved |
| checkpoint_6_package_review | approved |

## Pitfalls

1. **架构原则**：pipeline skill = 编排器 + 独立子skill，不要把所有逻辑塞进一个skill。参考 wechat-automation-pipeline-skill 的模式：pipeline 只负责状态机和 contracts，每个 step 调用独立的子skill，子skill 可单独复用。templates/ 目录保留在 pipeline 中作为输出格式参考，但实际生成逻辑在各子skill中。
2. **工作目录**：pipeline.py 的 `PROJECT_ROOT` 是相对路径 `outputs/book-distillation-pipeline-skill/`。必须从项目根目录（如 `~/`）运行，不能从 skill 目录内部运行，否则 outputs 会写到 skill 目录内。
3. **文件路径**：`--book-path` 必须是已存在的文件路径，否则 init 会报错。建议使用绝对路径。
4. **checkpoint approve 必须带 --value**：每个 approve 命令都需要 `--value approved`（或对应选项值），否则会报错 `requires --value`。
5. **子skill调用方式**：当前每个step需要agent手动调用对应子skill（skill_view + 按SKILL.md中的Prompt生成内容）。未来可考虑让pipeline.py自动调用子skill。
6. **交叉验证的精度**：cross-validation使用简单字符串匹配，可能遗漏语义相同但措辞不同的条目。验证后建议agent人工确认。
7. **person-series 特殊处理**：关于同一人物的多来源材料（访谈录、博客、问答），分类时通常用模板A（决策纠偏）为主，辅模块选人格模拟法的语音特征+场景回应库。作者原声提取需区分"他的原话"和"他人描述"。

## Sub-skills

本pipeline调用以下独立子skill（每个可单独使用）：

| Step | 子skill | 产出 |
|------|---------|------|
| 1 | `book-classifier-skill` | `01-classification.md` |
| 2 | `author-voice-extractor-skill` | `02-author-voice.md` |
| 3 | `instruction-generator-skill` | `03-instructions.md` |
| 4 | `knowledge-base-builder-skill` | `04-knowledge-base.md` |
| 5 | `cross-validator-skill` | `05-cross-validation.md` |
| 6 | `agent-packager-skill` | `06-package-config.md` |

## Failure Recovery

- 外部技能失败：保持在当前stage，说明失败原因
- 状态文件与磁盘不一致：先修正文件，再重新complete-action
- 用户要求回退：手动编辑 `.pipeline-state.json` 的 `current_stage`

## 书籍分类决策树

```
Q1: 教你"遇到情况如何思考/决策"？
    ├─ 是 → 【三层蒸馏法】（模板A）
    └─ 否 → Q2: 提供"看世界的独特透镜"？
              ├─ 是 → 【视角蒸馏法】（模板B）
              └─ 否 → Q3: 记录"高成就者的思维方式"？
                    ├─ 是 → 【人格模拟法】（模板C）
                    └─ 否 → Q4: 训练"伦理/逻辑思辨"？
                          ├─ 是 → 【论证映射法】（模板D）
                          └─ 否 → Q5: 提供"可直接执行的技能流程"？
                                ├─ 是 → 【技能拆解法】（模板E）
                                └─ 否 → 【案例-原则-行动法】（模板F）
```

## 混合类型处理

若书籍横跨多个类型，采用「主模板 + 1-2个辅模块」模式。辅模块≤2个。

## Response Template

每个checkpoint的对话结构：
1. 当前阶段名
2. 已生成的文件路径
3. 关键结果摘要
4. 明确问题：`是否继续到下一步？`

不要在checkpoint消息里偷偷继续执行下一步。
