# JadeFlow AI 图标仪表盘

这是 JadeFlow AI 前端页面的说明文档。

当前前端实现了一个企业级 Dashboard 首页，用于展示知识库、文档、工单、审批、执行链路追踪、数据分析、系统集成和配置等功能入口。页面采用青绿色山水背景、液态玻璃面板、自定义圆形图标和点击水波纹动效。

## 页面特性

- 使用 16:9 全屏背景图，不挤压、不拉伸
- 参考设计稿布局，还原左侧导航和右侧主内容区域
- 左上角 Logo 使用上传的 Logo 图片
- 统计卡片和功能卡片使用上传的小图标
- 保留液态玻璃质感
- 点击页面会出现水波纹扩散效果
- Day 2 已接入登录页和登录态保护

## 背景图尺寸

```text
1672 × 941
```

比例：

```text
1.776833
```

## 运行方式

前端需要连接后端接口。请先确认后端已经在 `http://localhost:8000` 启动，并且下面地址能返回正常结果：

```text
http://localhost:8000/health
```

默认使用 `3000` 启动当前项目的前端：

```bash
cd /Users/liuyiming/Desktop/project/ai_agent/frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev
```

访问：

```text
http://localhost:3000/login
```

如果 `3000` 被旧前端或其他服务占用，可以临时换到 `5173`：

```bash
cd /Users/liuyiming/Desktop/project/ai_agent/frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev -- -p 5173
```

访问：

```text
http://localhost:5173
```

登录页：

```text
http://localhost:5173/login
```

如果点击“进入仪表盘”失败，优先检查：

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
lsof -nP -iTCP:3000 -sTCP:LISTEN
lsof -nP -iTCP:5173 -sTCP:LISTEN
```

如果 `3000` 对应的工作目录是 `/Users/liuyiming/.Trash/frontend` 或 `/Users/liuyiming/.Trash/frontend 19.44.37`，说明浏览器打开的是旧前端，不是当前项目。关闭旧进程后重新启动当前前端：

```bash
kill <PID>
```

如果访问时提示 assets not found，先确认浏览器打开的是当前项目启动出来的地址。Next.js 只会把 `public/` 目录里的文件作为站点静态资源暴露出去：

```text
public/jade-river-bg.png   -> /jade-river-bg.png
public/icons/logo.png      -> /icons/logo.png
public/icons/*.png         -> /icons/*.png
```

如果使用 `5173` 备用端口，后端的 `FRONTEND_ORIGIN` 也要同步改成 `http://localhost:5173` 后重新启动。

## 单文件预览

直接打开：

```text
standalone/index.html
```

该文件只用于快速查看视觉效果，不包含真实登录接口。

## 关键文件

```text
public/jade-river-bg.png          # 16:9 背景图
public/icons/logo.png             # 左上角 logo
public/icons/*.png                # 所有小图标
components/Dashboard.tsx          # 主页面组件
lib/dashboard-data.ts             # 导航、统计、功能卡片数据
lib/auth.ts                       # 登录接口封装
lib/session.ts                    # 本地登录态存储
app/login/page.tsx                # 登录页
app/globals.css                   # 页面布局、玻璃效果、水波动画
standalone/index.html             # 无依赖预览版
```

## 图标对应关系

```text
logo.png                  左上角 Logo
knowledge-articles.png    知识文章统计卡
open-tickets-stat.png     待处理工单统计卡
resolved-tickets-stat.png 已解决工单统计卡
avg-resolution-time.png   平均解决时长统计卡
knowledge-base.png        知识库功能卡
documents.png             文档功能卡
tickets.png               工单功能卡
approvals.png             审批功能卡
agent-trace.png           执行链路追踪功能卡
analytics.png             数据分析功能卡
integrations.png          系统集成功能卡
settings.png              设置功能卡
```

## 布局修复说明

早期版本中，下方卡片重叠是因为右侧统计区和功能区使用了固定绝对定位：

```css
.stats-grid { top: 432px; }
.feature-grid { top: 572px; bottom: 68px; }
```

当浏览器窗口高度、系统缩放或字体渲染发生变化时，卡片实际高度可能超过预留高度，于是下面的功能卡片被顶上来，造成重叠。

当前版本已经修复：

- 右侧主内容改为 `.main-area` 自然文档流；
- 统计卡片和功能卡片不再用固定 `top` 堆叠；
- 小屏高度下会自动压缩间距、图标和字体；
- 如果高度仍然不够，右侧区域会出现滚动条，不再重叠。

## 图标修复说明

早期版本图标左上角出现“被侵蚀”的边缘，是因为处理上传图标时，自动把棋盘格背景转透明，算法把部分浅色高光也误判成背景透明区域。

当前版本重新处理了图标：

- 圆形图标改用圆形蒙版保留完整徽章；
- 不再直接删除徽章内部的浅色高光；
- 左上角的玻璃高光和边缘不会再被抠掉；
- 保留透明背景，放到页面中不会显示棋盘格。
