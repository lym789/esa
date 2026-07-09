# Day 16 设置页与退出登录

Day 16 补齐了前端设置页，并把退出登录入口放到设置页面中。用户从仪表盘点击“设置”后进入 `/settings`，可以查看当前账号信息并退出登录。

## 已完成内容

- 新增 `/settings` 设置页。
- 设置页读取本地登录状态并展示当前账号、邮箱和角色。
- 设置页新增“退出登录”按钮。
- 点击退出后清除 `localStorage` 中的登录状态，并跳转到 `/login`。
- Dashboard 的“设置”导航和功能卡片都跳转到 `/settings`。
- 移除侧边栏中只有图标的退出登录入口，避免入口不明显。

## 前端文件

```text
frontend/app/settings/page.tsx
frontend/components/Dashboard.tsx
frontend/lib/dashboard-data.ts
frontend/app/globals.css
```

## 页面入口

登录后进入仪表盘：

```text
http://localhost:3000
```

点击“设置”进入：

```text
http://localhost:3000/settings
```

设置页右侧“登录安全”卡片中提供“退出登录”按钮。

## 行为说明

- 未登录用户访问 `/settings` 会自动跳转到 `/login`。
- 已登录用户点击“退出登录”后，本机保存的登录状态会被清除。
- 退出后再次访问仪表盘、工单、审批、文档等页面需要重新登录。

## 验证

新增测试：

```text
tests/test_day16_frontend_settings_logout_scaffold.py
```

运行方式：

```bash
python3 -m unittest tests.test_day16_frontend_settings_logout_scaffold -v
cd frontend
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run build
```

## 当前限制

- 设置页当前只包含账号信息和退出登录。
- 暂未实现密码修改、偏好设置、通知设置和安全审计记录。

这些能力留到后续阶段继续补齐。
