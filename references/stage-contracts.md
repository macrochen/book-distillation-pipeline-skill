# Stage Contracts

本文档定义 `book-distillation-pipeline-skill` 每个阶段的输入、输出、审核标准和记账方式。

所有产物路径基于：`outputs/book-distillation-pipeline-skill/<yyyymmdd-slug>/`

## Step 0: Init

- 类型：action
- 输入：书籍文件路径（支持多个）、书名、作者名
- 支持格式：PDF、MD、Markdown、TXT、EPUB
- 项目类型：
  - `single`：单本书籍
  - `multi-book`：同一作者的系列书籍
  - `person-series`：关于同一人物的多来源材料
- 输出：
  - `00-book-info.md`（含所有书籍列表）
  - `.pipeline-state.json`
- 记账：自动完成

## Checkpoint 0: Book Info

- 类型：checkpoint
- 目标：确认书籍信息和目标平台
- 决策：
  - `book_info_confirmed`: confirmed
- 记账：
  ```bash
  python3 ${SKILL_DIR}/scripts/pipeline.py approve \
    --project-dir "outputs/book-distillation-pipeline-skill/<slug>" \
    --stage checkpoint_0_book_info --value confirmed
  ```

## Step 1: Classify → `book-classifier-skill`

- 类型：action
- 调用：`book-classifier-skill`
- 输入：
  - `00-book-info.md`（书籍列表、作者信息）
  - 所有书籍文件内容（PDF/MD/TXT）
- 必须输出：`01-classification.md`
- 多书场景：
  - 多本书通常共享同一主类型
  - 分类时考虑所有书籍的整体定位
  - 若类型差异大，以占比最大的为主，其他作为辅模块
- 用户可见检查点：
  - 展示分类结果（主类型、辅模块、选择理由）
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
- 记账：
  ```bash
  python3 ${SKILL_DIR}/scripts/pipeline.py approve \
    --project-dir "outputs/book-distillation-pipeline-skill/<slug>" \
    --stage checkpoint_1_classify_review
  ```

## Step 2: Author Voice → `author-voice-extractor-skill`

- 类型：action
- 调用：`author-voice-extractor-skill`
- 输入：
  - 所有书籍文件
  - `00-book-info.md`（作者名、项目类型）
- 必须输出：`02-author-voice.md`
- 多书场景：
  - 跨所有书籍提取统一的作者原声特征
  - person-series需区分"他的原话"和"他人描述"
  - 合并高频特征，标注来源书籍
- 用户可见检查点：
  - 展示口头禅、反问句式、比喻习惯等提取结果
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

## Step 3: Instructions → `instruction-generator-skill`

- 类型：action
- 调用：`instruction-generator-skill`
- 输入：
  - `01-classification.md`（确定使用哪个模板）
  - `02-author-voice.md`（作者原声）
  - 书籍内容
- 必须输出：`03-instructions.md`
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

## Step 4: Knowledge Base → `knowledge-base-builder-skill`

- 类型：action
- 调用：`knowledge-base-builder-skill`
- 输入：
  - `01-classification.md`
  - `03-instructions.md`
  - 书籍内容
- 必须输出：`04-knowledge-base.md`
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

## Step 5: Cross Validate → `cross-validator-skill`

- 类型：action
- 调用：`cross-validator-skill`
- 输入：
  - `03-instructions.md`
  - `04-knowledge-base.md`
- 必须输出：`05-cross-validation.md`
- 验证规则：
  - [ ] Instructions中所有标志性提问在Knowledge中有对应条目
  - [ ] Instructions中每个模型名称在Knowledge中有定义
  - [ ] Instructions冲突表中每条规则在Knowledge中有详细解释
  - [ ] 缺失项已标记并补充建议
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

## Step 6: Package → `agent-packager-skill`

- 类型：action
- 调用：`agent-packager-skill`
- 输入：
  - `01-classification.md`
  - `03-instructions.md`
  - `04-knowledge-base.md`
- 必须输出：`06-package-config.md`
- 内容：
  - 智能体名称
  - 说明（Description）
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
- 流程（半自动）：
  1. 打开目标平台创建页面（URL可配置）
  2. 自动复制名称到剪贴板
  3. 自动复制说明到剪贴板
  4. 自动复制指令到剪贴板
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
