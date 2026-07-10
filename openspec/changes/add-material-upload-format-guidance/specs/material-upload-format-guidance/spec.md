## ADDED Requirements

### Requirement: Show supported upload formats when users enter the materials page
资料页 MUST 在用户进入“简历”“职位 JD”“知识库”任一分区时，就向用户清晰展示当前支持的上传文件格式。该说明 MUST 不依赖用户先点开上传弹窗才可见，并 MUST 使用易懂文案列出 `PDF`、`DOCX`、`DOC`、`TXT`、`MD`。

#### Scenario: User opens the resume tab
- **WHEN** 用户进入资料页并查看“简历”分区
- **THEN** 页面在主内容或空状态中直接显示简历支持上传 `PDF、DOCX、DOC、TXT、MD`

#### Scenario: User opens the knowledge tab
- **WHEN** 用户进入资料页并查看“知识库”分区
- **THEN** 页面在不打开弹窗的情况下就能看到知识材料支持上传 `PDF、DOCX、DOC、TXT、MD`

### Requirement: Keep format guidance consistent across tabs and dialogs
系统 MUST 在资料页主界面、空状态和添加资料弹窗中保持一致的文件格式说明，不得出现某一处写支持 `DOCX/TXT/MD` 而另一处遗漏 `DOC` 或 `PDF` 的情况。若某个分区额外支持粘贴文本，系统 SHALL 将“文本粘贴能力”和“文件上传支持格式”分开描述。

#### Scenario: User opens the JD upload dialog
- **WHEN** 用户在“职位 JD”分区点击添加资料
- **THEN** 弹窗继续显示支持 `PDF、DOCX、DOC、TXT、MD`，并单独说明“也支持直接粘贴 JD 文本”

#### Scenario: User compares the library page and upload dialog
- **WHEN** 用户先阅读资料页，再打开任一上传弹窗
- **THEN** 两处看到的支持格式列表保持一致，不会产生冲突或歧义

### Requirement: Format guidance MUST NOT imply new upload behavior
文件格式说明 MUST 只表达当前支持的文件类型，不得暗示系统已经新增了解析能力、自动识别能力或收费变化。说明文案 MUST NOT 把“支持上传某种格式”误写成“已完成解析”或“上传后一定可用于面试”。

#### Scenario: User reads the upload note
- **WHEN** 用户查看资料页上的文件格式提示
- **THEN** 文案只说明支持哪些格式及必要的文本粘贴说明，不宣称新增了解析成功率、索引速度或免费额度
