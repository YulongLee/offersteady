/** Existing server stages and binding messages, without changing the API contract. */
export function writtenScreenshotFailureMessage(message: string, failureStage?: string): string {
  if (/电脑伴随程序心跳已过期|(?:本地助手|伴随程序|助手)已离线/.test(message)) {
    return "本地助手已离线，请保持助手打开并恢复连接后重新截屏。";
  }
  if (/这台电脑尚未登记或机器码不匹配|网页端尚未输入该机器码绑定面试|网页端绑定已失效|伴随程序已重新登记/.test(message)) {
    return "本地助手连接已失效，请重新连接后截屏。";
  }
  const stage = failureStage ?? message.match(/^截图阶段 ([a-z-]+) 失败：/)?.[1];
  if (stage === "capture-failed") return "截屏失败，请检查本地助手的共享屏幕或录制权限后重试。";
  if (stage === "upload-failed") return "截图上传失败，请检查网络后重新截屏。";
  return message;
}
