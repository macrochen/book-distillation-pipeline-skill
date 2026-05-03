# Stage Contracts

本文档定义 `book-distillation-pipeline-skill` 每个阶段的输入、输出、审核标准和记账方式。

所有产物路径基于：`outputs/book-distillation-pipeline-skill/<yyyymmdd-slug>/`

## Step 0: Init

- 类型：action
- 输入：书籍PDF路径、书名、作者名
- 输出：
  - `00-book-info.md`
  - `.pipeline-state.json`
- 记账：自动完成

## Checkpoint 0: Book Info

- 类型：checkpoint
- 目标：确认书籍信息和目标平台
- 决策：
  - `book_info_confirmed`: confirmed
- 可配置项：
  - 目标平台（gemini/chatgpt）
  - Gemini创建页面URL
- 记账：
  ```bash
  python3 ${SKILL_DIR}/scripts/pipeline.py approve \
    --project-dir "outputs/book-distillation-pipeline-skill/<slug>" \
    --stage checkpoint_0_book_info --value confirmed
  ```

## Step 1: Classify

- 类型：action
- 输入：`00-book-info.md`、书籍PDF
- 使用模板：`templates/classification-guide.md`
- 输出：`01-classification.md`
- 审核清单：
  - [ ] 主类型明确（六选一）
  - [ ] 辅模块≤2个
  - [ ] 选择理由充分
- 记账：
  ```bash
  python3 ${SKILL_DIR}/scripts/pipeline.py complete-action \
    --project-dir "outputs/book-distillation-pipeline-skill/<slug>" \
    --stage step_1_classify \
    --artifact classification_md="outputs/book-distillation-pipeline-skill/<slug>/01-classification.md"
  ```

## Checkpoint 1: Classify Review

- 类型：checkpoint
- 目标：展示分类结果，用户确认或修正
- 审核内容：主类型、辅模块、选择理由
- 记账：
  ```bash
  python3 ${SKILL_DIR}/scripts/pipeline.py approve \
    --project-dir "outputs/book-distillation-pipeline-skill/<slug>" \
    --stage checkpoint_1_classify_review
  ```

## Step 2: Author Voice

- 类型：action
- 输入：书籍PDF
- 使用模板：`templates/author-voice-prompt.md`
- 输出：`02-author-voice.md`
- 审核清单：
  - [ ] 口头禅≥3个
  - [ ] 反问句式≥3个
  - [ ] 比喻习惯≥3个
  - [ ] 每项有原文出处
  - [ ] 抽查3处原文存在
- 记账：
  ```bash
  python3 ${SKILL_DIR}/scripts/pipeline.py complete-action \
    --project-dir "outputs/book-distillation-pipeline-skill/<slug>" \
    --stage step_2_author_voice \
    --artifact voice_md="outputs/book-distillation-pipeline-skill/<slug>/02-author-voice.md"
  ```

## Checkpoint 2: Voice Review

- 类型：checkpoint
- 目标：展示作者原声提取结果
- 记账：
  ```bash
  python3 ${SKILL_DIR}/scripts/pipeline.py approve \
    --project-dir "outputs/book-distillation-pipeline-skill/<slug>" \
    --stage checkpoint_2_voice_review
  ```

## Step 3: Instructions

- 类型：action
- 输入：
  - `01-classification.md`（确定使用哪个模板）
  - `02-author-voice.md`（作者原声）
  - 书籍PDF
- 使用模板：
  - `templates/common-header-protocol.md`
  - `templates/instructions-template-{A/B/C/D/E/F}.md`
- 输出：`03-instructions.md`
- 审核清单：
  - [ ] 通用头部协议在最顶部
  - [ ] 身份定义完整
  - [ ] 核心模型≥3个，每个有语义触发+关键词触发
  - [ ] 冲突表≥2条
  - [ ] 决策协议≥3个，有IF-THEN
  - [ ] 反模式禁令≥5条
  - [ ] 输出格式模板完整
  - [ ] 标志性提问有原文出处
- 记账：
  ```bash
  python3 ${SKILL_DIR}/scripts/pipeline.py complete-action \
    --project-dir "outputs/book-distillation-pipeline-skill/<slug>" \
    --stage step_3_instructions \
    --artifact instructions_md="outputs/book-distillation-pipeline-skill/<slug>/03-instructions.md"
  ```

## Checkpoint 3: Instructions Review

- 类型：checkpoint
- 目标：展示指令全文，按审核清单检查
- 记账：
  ```bash
  python3 ${SKILL_DIR}/scripts/pipeline.py approve \
    --project-dir "outputs/book-distillation-pipeline-skill/<slug>" \
    --stage checkpoint_3_instructions_review
  ```

## Step 4: Knowledge Base

- 类型：action
- 输入：
  - `01-classification.md`
  - `03-instructions.md`
  - 书籍PDF
- 使用模板：`templates/knowledge-base-template-{A/B/C/D/E/F}.md`
- 输出：`04-knowledge-base.md`
- 审核清单：
  - [ ] 条目数≥15
  - [ ] 每个条目有标签、出处、证据
  - [ ] 每个条目有反对意见+作者回应
  - [ ] 时效性数据有声明（如适用）
- 记账：
  ```bash
  python3 ${SKILL_DIR}/scripts/pipeline.py complete-action \
    --project-dir "outputs/book-distillation-pipeline-skill/<slug>" \
    --stage step_4_knowledge_base \
    --artifact kb_md="outputs/book-distillation-pipeline-skill/<slug>/04-knowledge-base.md"
  ```

## Checkpoint 4: KB Review

- 类型：checkpoint
- 目标：展示知识库条目数量和关键条目预览
- 记账：
  ```bash
  python3 ${SKILL_DIR}/scripts/pipeline.py approve \
    --project-dir "outputs/book-distillation-pipeline-skill/<slug>" \
    --stage checkpoint_4_kb_review
  ```

## Step 5: Cross Validate

- 类型：action
- 输入：`03-instructions.md`、`04-knowledge-base.md`
- 输出：`05-cross-validation.md`
- 验证规则：
  - [ ] Instructions中所有标志性提问在Knowledge中有对应条目
  - [ ] Instructions中每个模型名称在Knowledge中有定义
  - [ ] Instructions冲突表中每条规则在Knowledge中有详细解释
  - [ ] 缺失项已补充
- 记账：
  ```bash
  python3 ${SKILL_DIR}/scripts/pipeline.py complete-action \
    --project-dir "outputs/book-distillation-pipeline-skill/<slug>" \
    --stage step_5_cross_validate \
    --artifact validation_md="outputs/book-distillation-pipeline-skill/<slug>/05-cross-validation.md"
  ```

## Checkpoint 5: Validate Review

- 类型：checkpoint
- 目标：展示验证结果
- 如有缺失：返回对应步骤补充
- 记账：
  ```bash
  python3 ${SKILL_DIR}/scripts/pipeline.py approve \
    --project-dir "outputs/book-distillation-pipeline-skill/<slug>" \
    --stage checkpoint_5_validate_review
  ```

## Step 6: Package

- 类型：action
- 输入：`01-classification.md`、`03-instructions.md`、`04-knowledge-base.md`
- 输出：`06-package-config.md`
- 内容：
  - 智能体名称
  - 说明（Description）
  - 指令摘要
  - Conversation Starters（3个）
  - 安全免责声明
- 记账：
  ```bash
  python3 ${SKILL_DIR}/scripts/pipeline.py complete-action \
    --project-dir "outputs/book-distillation-pipeline-skill/<slug>" \
    --stage step_6_package \
    --artifact package_md="outputs/book-distillation-pipeline-skill/<slug>/06-package-config.md"
  ```

## Checkpoint 6: Package Review

- 类型：checkpoint
- 目标：展示打包配置
- 记账：
  ```bash
  python3 ${SKILL_DIR}/scripts/pipeline.py approve \
    --project-dir "outputs/book-distillation-pipeline-skill/<slug>" \
    --stage checkpoint_6_package_review
  ```

## Step 7: Deploy

- 类型：action
- 输入：`06-package-config.md`、`04-knowledge-base.md`
- 流程：
  1. 打开目标平台创建页面
  2. 复制名称到剪贴板
  3. 复制说明到剪贴板
  4. 复制指令到剪贴板
  5. 用户手动上传知识库MD文件
  6. 用户手动保存
- 记账：
  ```bash
  python3 ${SKILL_DIR}/scripts/pipeline.py complete-action \
    --project-dir "outputs/book-distillation-pipeline-skill/<slug>" \
    --stage step_7_deploy \
    --meta platform=gemini \
    --meta deploy_status=completed
  ```
