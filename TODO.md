# 需求

## [x] 日语（句子）反向卡片，显示的是中文，但我不知道是要回答日语还是英语；需要再哪里提示出来，其他卡片也检查一下这个问题。

> 2026-08-25 已修复：句子卡片 Production 正面已增加 `target_language` 字段标注（eyebrow `Production · Japanese/English` + 提示 `Translate to {{target_language}}`），旧笔记类型自动迁移新增字段。Word/Phrase 卡片检查：`Recognition` 与 `Recall/Spelling` 已通过卡片类型和 deck 区分方向，暂无同类歧义，无需额外标注。
> 后两项（单词图片开关、图形界面）已完成并移除。
