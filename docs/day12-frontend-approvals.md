# Day 12 前端审批页面

Day 12 补齐了审批前端页面。审批人和管理员可以从仪表盘点击“审批”进入审批中心，查看 `pending` 审批详情，并通过或拒绝 `urgent` 工单创建请求。普通员工可以查看自己发起的审批记录，但不能执行审批动作。

## 已完成内容

- 新增审批前端 API client。
- 新增 `/approvals` 页面。
- Dashboard 的“审批”卡片跳转到 `/approvals`。
- 支持查看当前账号可见的审批列表。
- 支持查看审批详情、风险原因、工具参数和执行结果。
- 支持审批人或管理员填写审批意见后通过审批。
- 支持审批人或管理员填写审批意见后拒绝审批。
- 审批页面和列表区域支持滚动，避免详情内容被窗口底部截断。

## 前端文件

```text
frontend/lib/approvals.ts
frontend/app/approvals/page.tsx
frontend/app/globals.css
frontend/lib/dashboard-data.ts
```

## 页面入口

登录后访问：

```text
http://localhost:3000/approvals
```

或从仪表盘点击“审批”功能卡片进入。

## 使用流程

1. 员工在 `/tickets` 页面创建优先级为 `urgent` 的工单。
2. 后端不会直接创建工单，而是返回 `pending_approval` 和审批编号。
3. 审批人登录 `approver@example.com`，进入 `/approvals`。
4. 审批人查看工具参数、风险原因和工单描述。
5. 点击“通过审批”后，后端恢复执行原 `create_ticket` 工具调用并创建工单。
6. 点击“拒绝审批”后，后端保存审批意见，不创建工单。

## 权限行为

- `employee`：可以查看自己发起的审批记录，不能通过或拒绝。
- `approver`：可以查看审批列表，可以通过或拒绝审批。
- `admin`：可以查看全部审批，可以通过或拒绝审批。
- 未登录用户访问 `/approvals` 会跳转到登录页。

## 验证

新增脚手架测试：

```text
tests/test_day12_frontend_approvals_scaffold.py
```

运行方式：

```bash
python3 -m unittest tests.test_day12_frontend_approvals_scaffold -v
```

前端构建：

```bash
cd frontend
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run build
```

后端审批接口测试：

```bash
conda run -n esa python -m pytest backend/tests/test_approval_service.py backend/tests/test_approvals_api.py -q
```

## 当前限制

- 当前审批页只覆盖 `create_ticket` 这一类工具审批。
- 暂未实现审批列表筛选、分页和搜索。
- 暂未实现工单详情页联动跳转。
- 暂未实现审批通知。

这些能力留到后续阶段继续补齐。
