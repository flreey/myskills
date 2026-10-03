# 来源与许可

## 数据来源

- 项目：YouMind OpenLab 的 `awesome-gpt-image-2`
- 仓库：https://github.com/YouMind-OpenLab/awesome-gpt-image-2
- 本地同步源：仓库主分支的 `README_zh.md`
- 在线完整图库：https://youmind.com/zh-CN/gpt-image-2-prompts

本地 SQLite 目录只索引 GitHub README 当前公开展示的精选和分类样本。README 的统计数字可能代表在线图库总量，不等于本地实际条目数。以 `sync_catalog.py` 输出的 `record_count` 作为本地覆盖范围，不要对用户声称本地包含在线图库的全部内容。

## 许可与署名

上游仓库将提示词集合标为 Creative Commons Attribution 4.0 International（CC BY 4.0）。改编具体条目时：

1. 保留上游项目名称和仓库链接。
2. 优先附上检索结果中的原始来源链接或 YouMind 详情链接。
3. 明确提示词经过了改写，不暗示原作者认可改编结果。
4. 不把预览图片重新打包进本 Skill；只保存其远程 URL。

许可证正文：https://creativecommons.org/licenses/by/4.0/

## 更新边界

同步脚本只执行只读 HTTP 请求，并原子替换本地 SQLite 目录。它不调用上游需要 API Key 的 CMS 接口，也不会向 YouMind 或 GitHub 写入数据。若公开 README 的结构变化导致解析条目过少，脚本会拒绝覆盖已有目录。
