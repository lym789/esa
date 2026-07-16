# Day 23：企业级 RAG Phase 4——可信回答与安全治理

## 本阶段结果

Phase 4 核心能力已经落地，目标是让“有检索结果”进一步升级为“证据可核验、权限不越界、恶意内容不进入回答、Trace 不泄密”。

### 1. Claim 级引用与证据校验

- LLM 输出升级为 `answer + claims + citations + confidence + answerability`。
- 每个 claim 必须引用本次检索实际返回的 chunk UID 或合法序号。
- 对金额、日期、比例等数字事实检查其是否出现在引用证据中。
- 对 claim 与证据执行词项覆盖检查；无依据的 claim 会触发安全降级。
- 支持 `answerable / partial / unanswerable`，证据不足时不伪装成确定答案。

当前校验器是确定性启发式实现，优点是低延迟、可复现、容易作为强制门禁。后续可在人工黄金集上校准 NLI 或 LLM Judge，但不能用未经校准的 Judge 替代硬性引用边界。

### 2. Prompt Injection 防护

- 用户问题在意图识别和检索前执行中英文注入特征检测。
- 命中攻击特征时直接返回统一安全提示，并记录 `security_refusal` Trace。
- 文档 chunk 在召回融合前再次检查，恶意知识内容不会进入 rerank、上下文和 LLM。
- 系统 Prompt 明确把检索片段视为数据而不是指令。

该实现采用入口与知识库双边界，覆盖“用户诱导模型绕过规则”和“被污染文档向模型下指令”两类风险。

### 3. Trace 脱敏

Trace 写入前递归处理字符串、列表和对象，默认遮蔽：

- 邮箱地址；
- 中国大陆手机号；
- `sk-` 风格密钥；
- Bearer Token；
- password、secret、token、api_key 等敏感字段值。

用户输入、LLM 输入摘要、LLM 输出和错误信息均经过同一层处理，避免只保护正常链路却从异常日志泄漏。

### 4. 部门 ACL 与文档分级

- 用户新增 `department_id`。
- 文档新增 `classification`：`public / internal / confidential / restricted`。
- 新增文档—部门授权表，支持一份文档授权多个部门。
- 受限文档满足“角色授权或部门授权”任一条件才能进入检索。
- ACL 与发布状态、有效期、知识库过滤一起进入数据库查询条件。
- `confidential / restricted` 分级强制使用 `restricted` 可见性。
- 管理员治理 API 可原子替换角色与部门授权。

权限判断发生在 PostgreSQL 查询阶段，不采用“先召回再从应用层删除”的不安全方式。管理员仍保留运维级全局访问能力。

### 5. 数据库变更

幂等迁移 `0005_department_acl_and_classification` 包含：

- `users.department_id`；
- `documents.classification`；
- `document_department_acls` 及唯一约束；
- 对应查询索引。

迁移已应用到本地 PostgreSQL 验证库。

## 验证结果

- Phase 4 定向测试：49 passed。
- 后端完整回归：144 passed，1 skipped。
- 根目录 scaffold 回归：53 passed。
- PostgreSQL + pgvector 集成：1 passed。

PostgreSQL 集成测试同时覆盖公开文档、角色授权受限文档、部门授权受限文档和 lexical 精确编号召回。

## 已知边界与后续工作

- 部门标识目前是业务字符串，生产接入时应由企业组织目录同步，避免自由输入造成命名漂移。
- 用户组 ACL 尚未实现；如企业权限模型依赖动态群组，应增加 group membership 快照或目录实时校验。
- Prompt Injection 检测目前为规则门禁，需要持续用红队样本补充编码变体、间接注入和多语言攻击。
- Trace 已脱敏但尚未包含细粒度审计访问策略与保留期限。
- Claim 依据校验尚未引入经过黄金集校准的语义蕴含模型。
