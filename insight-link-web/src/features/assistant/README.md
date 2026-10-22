# 学业 AI 助手前端

- `AssistantWorkspace.vue`：对话、材料选择、人工补充表单和操作确认的页面状态。
- `AssistantWorkspace.css`：页面样式，由组件以 `scoped` 方式加载。
- `assistantContent.js`：对话标题、材料说明、附件标记及安全 Markdown 渲染。
- `useAssistantArtifacts.js`：图表预览与报告下载；切换对话时撤销旧的浏览器对象 URL。
- `AssistantProgress.vue`：可展开的任务步骤、专家协作、工具状态与复核结果。
- `useAssistantProgress.js`：归并本轮 SSE 事件；切换会话恢复 Mongo 中的安全 Harness 摘要。
- `useAssistantExecution.js`：独立管理执行任务、停止确认、状态轮询和恢复资格；用会话代次、任务 ID 与 attempt 隔离迟到响应。
- `useAssistantHistory.js`：服务端历史搜索和分页，排除旧请求覆盖新结果。
- `GradingStandardDialog.vue`：当前导师的长期 AI 评分标准，查看默认、编辑、恢复默认及版本冲突提示。

路由入口是 `src/views/TeacherAssistantPage.vue`。Agent 请求统一走 `src/api/agentHttp.js`，它按请求附带当前登录令牌；材料选择列表沿用 Java 后端的分页接口，选中后再调用 Agent 的材料摘要接口验权。对话中的能力评价和留言先进入补充、预览流程，导师确认后才执行。

消息使用 POST `/api/chat/messages/stream`，通过 fetch 请求头传递 token，不使用 URL 参数。`src/api/sse.js` 解析跨分片 UTF-8、多行 data、CRLF 和心跳；`src/api/assistantStream.js` 区分正式答复、已确认的中断与连接丢失。页面先展示真实处理过程，校验和持久化完成后才展示正文及文件卡；不展示模型推理、工具参数或原始结果。

当前会话 ID 记录到路由 query，刷新后重新鉴权读取该会话。运行中的任务只观察和轮询，绝不自动重发。点击“停止”会调用服务端执行取消接口，`cancel_requested` 显示“正在停止”，收到 `cancelled` 才显示“已停止”；`committing` 保存阶段禁止停止。弱网中停止请求失败先查询真实状态，无法核实时明确显示待核实。已停止、中断或失败的任务只有服务端明确给出 `can_resume: true` 才展示恢复按钮；恢复发送执行 ID 和已观察到的 attempt，由服务端读取原问题，使用当前登录令牌，不追加相同的用户消息。停止也携带 attempt，避免旧窗口按钮影响同一任务的新一次尝试。离开页面仅停止接收，不主动取消服务器任务。补字段、待确认预览及正式业务写入保留原有人工确认流程。

运行 `node --test tests/*.test.js` 验证流式协议、执行竞态与助手状态，`npm run build` 检查前端构建。

“评分标准”通过 `GET/POST /api/grading-standard` 操作当前登录导师的专属配置，无需前端传导师 ID。未自定义时显示系统按材料类型的默认量表；保存使用版本校验。AI 评分草稿展示生成时的标准，更新配置后可重新生成建议，既有正式成绩不会自动改变。
