# Day 10 前端 Trace 页面

Day 10 在 Day 9 后端 Trace 能力上补齐了管理员前端页面。管理员可以从仪表盘进入智能体追踪页，查看 Trace 列表和详情。

本阶段只实现 Trace 页面，不新增 Chat、工单、审批前端工作流。

## 已完成内容

- 新增 Trace 前端 API client。
- 新增 `/admin/traces` 页面。
- Dashboard 的“智能体追踪”卡片跳转到 `/admin/traces`。
- 管理员可以查看 Trace 列表和详情。
- 非管理员访问页面时显示权限提示。
- 页面展示意图、工具调用、审批状态、耗时、用户输入、智能体输出、工具参数、检索摘要和最终结果。

## 前端文件

```text
frontend/lib/traces.ts
frontend/app/admin/traces/page.tsx
frontend/app/globals.css
frontend/lib/dashboard-data.ts
```

## 页面入口

登录管理员账号后访问：

```text
http://localhost:3000/admin/traces
```

或从仪表盘点击“智能体追踪”功能卡片进入。

## 权限规则

- `admin`：可以加载 Trace 列表和详情。
- 其他角色：可以进入页面，但只看到权限提示，不会请求 Trace 数据。
- 未登录用户：自动跳转到 `/login`。

## 展示字段

列表展示：

- 意图类型
- 工具调用名称
- 审批状态
- 创建时间

详情展示：

- 意图
- 工具调用
- 审批状态
- 执行耗时
- 用户输入
- 智能体输出
- 意图识别 JSON
- 工具参数 JSON
- 检索摘要 JSON
- 最终结果 JSON
- 错误信息

## 验证

新增脚手架测试：

```text
tests/test_day10_frontend_traces_scaffold.py
```

运行方式：

```bash
python3 -m unittest tests.test_day10_frontend_traces_scaffold -v
```

前端构建：

```bash
cd frontend
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run build
```

## 下一阶段

下一阶段建议补 Chat、工单和审批前端页面：

- 员工在页面内发起知识问答。
- 从自然语言生成工单草稿。
- 员工确认创建普通工单或 urgent 审批。
- 审批人查看待审批记录并通过/拒绝。
