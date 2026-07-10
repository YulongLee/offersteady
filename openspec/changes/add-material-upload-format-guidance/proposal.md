## Why

当前资料页虽然在部分弹窗里限制了可选文件类型，但用户进入页面时并不能直观看到支持上传哪些格式，容易在准备资料前产生犹豫或试错。补上明确的格式说明，可以降低首次使用门槛，也能减少“上传什么内容才可以”的疑问。

## What Changes

- 在资料页为简历、JD 和知识库材料补充可上传文件格式说明，让用户进入页面时就能看到支持的格式范围。
- 统一资料页主界面、空状态和上传弹窗中的文件格式文案，明确支持 `pdf`、`docx`、`doc`、`txt`、`md`。
- 区分“文件上传支持格式说明”和“是否也支持粘贴文本”的表达，避免把 JD 的文本粘贴能力和文件格式能力混在一起。
- 不修改后端上传逻辑、解析逻辑、收费逻辑或资料选择流程，只调整说明信息的可见性与一致性。

## Capabilities

### New Capabilities
- `material-upload-format-guidance`: 定义资料页如何向用户清晰展示支持上传的文件格式和相关说明

### Modified Capabilities
- None

## Impact

- Affected frontend: `apps/web/src/LibraryManager.tsx` 及相关资料页文案与测试
- Affected UX: 首次进入资料页、空状态、添加简历 / JD / 知识材料弹窗的说明一致性
- No backend/API impact: 不改变上传接口、文件解析、索引或计费行为
