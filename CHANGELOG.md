# Changelog

## [Unreleased]

## [1.3.0] - 2026-09-20

### Added

- 页面 SEO 内容区：差异化定位说明、使用教程、适用人群和常见问题（FAQ），新增 FAQPage 结构化数据。
- `og-image.png` 分享预览图与完整的 Open Graph / Twitter Card 大图元信息。
- IndexNow 密钥文件，用于必应等搜索引擎主动收录。
- 静态资源 Cache-Control：字体一年不可变缓存、图片等一天、HTML 短缓存并带 `s-maxage` 供 CDN 边缘缓存。

### Changed

- 站名与区块标题改为语义化 H1/H2 层级，补充面向长尾关键词的标题和描述。
- 志莽行书（Zhi Mang Xing，OFL）改为自托管子集字体（2.7KB），不再依赖 Google Fonts，改善国内加载；CSP 移除 `fonts.googleapis.com` / `fonts.gstatic.com`。

## [1.2.0] - 2026-07-29

### Added

- IndexedDB 本地自动保存与刷新恢复。
- `.atd.json` 项目文件无损导入导出。
- 三并发批量上传队列、进度展示和失败统计。
- 按文件名批量收录与重复字冲突保护。
- 请求体、上传文件、图片像素、字形总量、请求频率和 CPU 并发限制。
- 基础安全响应头、自动化测试和 push/PR CI。

### Changed

- 将图片处理方式改为面向素材场景的中文名称。
- CPU 密集型任务移入线程池，避免阻塞 FastAPI 事件循环。
- 精简桌面构建依赖与过时模块，统一发布包文件名。
- README 更新为当前无状态、本地优先架构。

### Fixed

- 强去噪流程未使用 closing 结果的问题。
- 图片裁剪遗漏最末行、最末列像素的问题。
- 预览字体 Object URL 未释放的问题。
