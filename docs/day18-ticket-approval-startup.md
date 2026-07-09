# Day 18：工单列表、审批跳转和本地启动整理

## 本日目标

Day 18 补齐三个影响日常演示和调试的体验点：

- 工单中心支持搜索、状态筛选、优先级筛选和分页。
- 审批中心支持按审批状态筛选，审批通过并生成工单后可以直接跳转到对应工单详情。
- 根目录新增本地启动辅助脚本，减少反复手动查端口、杀端口和启动服务的成本。

## 工单列表增强

`frontend/app/tickets/page.tsx` 新增了本地筛选状态：

- `ticketSearchText`：搜索工单编号、标题、描述、分类、状态和优先级。
- `ticketStatusFilter`：按 `open`、`in_progress`、`resolved`、`closed` 筛选。
- `ticketPriorityFilter`：按 `low`、`medium`、`high`、`urgent` 筛选。
- `currentPage`：控制当前分页。

工单数据仍然来自后端 `/api/tickets`。当前筛选和分页在前端完成，适合 MVP 阶段的小规模演示数据。后续如果工单量变大，可以把筛选条件下沉到后端接口。

## 审批体验增强

`frontend/app/approvals/page.tsx` 新增了审批状态筛选：

- 全部审批
- 只看待审批
- 已通过
- 已拒绝

当审批记录的 `execution_result.ticket_id` 存在时，详情区会显示“查看工单”按钮，点击后进入 `/tickets/{ticket_id}`。这样审批人通过紧急工单后，可以直接查看实际创建出来的工单。

## 本地启动辅助脚本

根目录新增三个脚本：

```bash
./scripts/check-ports.sh
./scripts/start-local.sh
./scripts/stop-local.sh
```

用途：

- `check-ports.sh`：检查 PostgreSQL、后端、前端和常见备用前端端口。
- `start-local.sh`：按当前推荐流程启动 Docker PostgreSQL、`esa` conda 环境下的后端，以及 3000 端口前端。
- `stop-local.sh`：关闭 8000、3000、5173 端口的本地服务，并尝试停止 Docker PostgreSQL。

默认端口：

- PostgreSQL：5432
- 后端：8000
- 前端：3000

如果需要换端口，可以在执行脚本前传入环境变量：

```bash
FRONTEND_PORT=5173 ./scripts/start-local.sh
```

## 验收点

- 工单中心可以搜索和筛选工单。
- 工单列表超过单页数量时，可以上一页/下一页翻页。
- 审批中心可以快速切换待审批、已通过和已拒绝列表。
- 已通过并生成工单的审批记录可以直接跳到工单详情。
- README 中有脚本启动、检查端口和停止服务的说明。
