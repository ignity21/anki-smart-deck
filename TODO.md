# 后续计划

## 显示验证

- [ ] 深色主题 — 所有卡片模板在 Anki nightMode 下的显示效果验证
- [ ] 移动设备 — 在 Anki 移动端上验证卡片布局和交互

## STEM 卡片扩展

- [ ] 新增卡片类型：`comparison`（概念对比）、`cheatsheet`（速查表）、`proof`（证明题）、`code_snippet`（代码片段）、`visualization`（纯图表概念卡）

## 模板与 UI

- [ ] 模板风格统一 — math 集和其余几套模板的视觉风格差异很大，需要统一
- [ ] Card 预览工具 — `ankinote preview` 命令直接渲染 HTML，无需启动 Anki

## 文档与开发者体验

- [ ] 补全 `docs/NoteType.md` 和 `docs/cli.md`
- [ ] 创建 `.env.example` 文件

## CLI 功能补齐

- [ ] 暴露 `ankinote math` 子命令
- [ ] 暴露 word 集的拼写卡片（spelling）生成模式
- [ ] 语言卡片（word/phrase/sentence）支持 AI 生成配图，而不只是搜图
  - 目前仅有 STEM/Math 用 Gemini 生成图片

## 测试

- [ ] stem collection 单元测试
- [ ] math collection 单元测试
  - 当前只有集成测试

## 其他

- [ ] 错误日志和提示优化
- [ ] 图片生成支持（如配置中允许使用照片）
- [ ] 模板风格一致性
  - 当前 word/phrase/sentence/stem 共享一套暖色调大圆角风格
  - math 使用独立蓝色调小圆角风格
  - 用户会感觉不是一个产品
