/** Stable outgoing capture failure copy; no identifiers or provider content. */
const globalScreenshotFailures: Readonly<Record<string, string>> = {
  "截屏等待超时，请重试。": "Screen capture timed out. Try again.",
  "未能截取当前屏幕，请在助手确认屏幕选择和录制权限后重试。": "Could not capture the current screen. Check the screen selection and recording permission, then retry.",
  "截图回传超时，请查看网页状态后重试。": "Screenshot upload timed out. Check the web status before retrying.",
  "截图回传失败，请检查连接后重试。": "Screenshot upload failed. Check the connection and try again.",
  "暂时无法确认截图请求，请检查助手连接后重试。": "Could not confirm the screenshot request. Check the companion connection and retry.",
  "截图请求较多，请稍候重试。": "Too many screenshot requests. Try again shortly.",
  "截图请求等待过久，请重新截屏。": "The screenshot request expired. Capture again.",
  "截图回传结果尚未确认，请查看网页状态。": "Screenshot upload is not confirmed. Check the status on the web page.",
  "屏幕截取仍在恢复，请重新打开助手后重试。": "Screen capture is still recovering. Reopen the companion and retry.",
  "没有找到可截取的屏幕，请检查屏幕录制权限。": "No screen source was found. Check screen recording permission.",
};

export const screenshotFailureMessage = (global: boolean, message: string): string => {
  if (!global || !/[\u3400-\u9fff]/.test(message)) return message;
  return globalScreenshotFailures[message]
    ?? "Screen capture or upload failed. Check device permissions and the companion connection, then try again.";
};
