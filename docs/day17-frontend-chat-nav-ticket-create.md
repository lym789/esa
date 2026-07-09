# Day 17 AI 助手、导航接入与工单创建体验

Day 17 补齐了三个前端体验断点：AI 助手页面接入 Chat API，首页左侧导航接入已有真实页面，工单创建草稿支持手动调整优先级并明确显示创建按钮。

## 已完成内容

- 新增 Chat 前端 API client。
- 新增 `/chat` AI 助手页面。
- AI 助手页面支持查看对话列表、新建对话、发送消息和展示引用来源。
- 首页“询问 AI 助手”按钮跳转到 `/chat`。
- 首页左侧导航接入已有页面：
  - `知识库` -> `/chat`
  - `文档` -> `/admin/documents`
  - `工单` -> `/tickets`
  - `审批` -> `/approvals`
  - `智能体追踪` -> `/admin/traces`
  - `设置` -> `/settings`
- 工单草稿生成后可以手动调整标题、分类、优先级和问题描述。
- 工单草稿的普通工单按钮文案改为“创建工单”。
- 工单草稿选择“紧急”时按钮显示“提交审批”，并触发 urgent 审批流程。

## 前端文件

```text
frontend/lib/chat.ts
frontend/app/chat/page.tsx
frontend/app/tickets/page.tsx
frontend/components/Dashboard.tsx
frontend/lib/dashboard-data.ts
frontend/app/globals.css
```

## 页面入口

AI 助手：

```text
http://localhost:3000/chat
```

工单中心：

```text
http://localhost:3000/tickets
```

首页左侧导航和首页“询问 AI 助手”按钮都已经接入真实页面。

## 使用流程

### AI 助手

1. 登录后进入 `/chat`。
2. 系统加载已有对话；如果没有对话，会自动创建一个新对话。
3. 输入问题并点击“发送”。
4. 页面展示用户消息、AI 回复和引用来源。

### 工单创建

1. 登录后进入 `/tickets`。
2. 输入问题描述并点击“生成草稿”。
3. 检查或调整标题、分类、优先级和问题描述。
4. 优先级不是“紧急”时点击“创建工单”。
5. 优先级是“紧急”时点击“提交审批”，审批人到 `/approvals` 处理。

## 验证

新增脚手架测试：

```text
tests/test_day17_frontend_chat_nav_ticket_create_scaffold.py
```

运行方式：

```bash
python3 -m unittest tests.test_day17_frontend_chat_nav_ticket_create_scaffold -v
cd frontend
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run build
```

## 当前限制

- AI 助手当前使用 Day 6 的保守 RAG 回答，不调用真实 LLM。
- Chat 页面暂未支持删除对话、重命名对话和从回答一键创建工单。
- 左侧导航中的“数据分析”和“系统集成”还没有真实页面。

这些能力留到后续阶段继续补齐。
