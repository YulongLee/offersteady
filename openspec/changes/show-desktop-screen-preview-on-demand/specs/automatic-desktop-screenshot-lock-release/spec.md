## ADDED Requirements

### Requirement: Screenshot lock releases automatically
桌面伴随程序 SHALL 仅在一次预览捕捉或正式截屏处理期间持有截图互斥锁，并 SHALL 在该操作成功或失败结束后自动释放锁。

#### Scenario: Manual preview capture finishes
- **WHEN** 用户点击“预览”且本地捕捉成功或失败
- **THEN** 系统在本次捕捉结束后自动释放互斥锁
- **AND** 用户无需执行取消操作即可再次预览

#### Scenario: Remote or shortcut screenshot finishes
- **WHEN** 网页端或快捷键触发的截图完成捕捉与上传，或以失败结束
- **THEN** 系统自动释放互斥锁并恢复预览控件
- **AND** 同一时刻仍不得并行执行多个截图任务
