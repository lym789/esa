# Day 11 前端工单页面

Day 11 补齐了工单前端页面。用户可以从仪表盘点击“工单”进入工单中心，使用自然语言生成工单草稿，并确认创建普通工单；如果草稿优先级为 `urgent`，前端会显示已进入审批。

## 已完成内容

- 新增工单前端 API client。
- 新增 `/tickets` 页面。
- Dashboard 的“工单”卡片跳转到 `/tickets`。
- 支持自然语言生成工单草稿。
- 支持确认创建普通工单。
- 支持 urgent 工单提交审批后的提示。
- 工单草稿优先级手动选择已在 Day 17 补齐。
- 支持查看当前账号可见的工单列表。

## 前端文件

```text
frontend/lib/tickets.ts
frontend/app/tickets/page.tsx
frontend/app/globals.css
frontend/lib/dashboard-data.ts
```

## 页面入口

登录后访问：

```text
http://localhost:3000/tickets
```

或从仪表盘点击“工单”功能卡片进入。

## 页面能力

左侧是工单草稿区：

- 输入自然语言问题描述。
- 调用 `/api/tickets/draft` 生成标题、描述、分类和优先级。
- Day 17 起可以手动调整标题、分类、优先级和问题描述。
- 用户确认后调用 `/api/tickets` 创建工单。
- 如果是 `urgent`，后端返回 `pending_approval`，页面显示审批编号。

右侧是工单列表：

- employee 查看自己提交的工单。
- handler 查看分配给自己的工单。
- admin 查看全部工单。

## 验证

新增脚手架测试：

```text
tests/test_day11_frontend_tickets_scaffold.py
```

运行方式：

```bash
python3 -m unittest tests.test_day11_frontend_tickets_scaffold -v
```

前端构建：

```bash
cd frontend
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run build
```

## 当前限制

- 工单详情页和状态更新已在 Day 13 补齐。
- 工单评论已在 Day 14 补齐。
- 工单分配已在 Day 15 补齐。
- 审批人前端审批页面已在 Day 12 补齐。

这些能力留到后续阶段继续补齐。
