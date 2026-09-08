import fs from "node:fs";
import path from "node:path";
import ts from "typescript";

const desktopRoot = path.resolve(import.meta.dirname, "..");
const sourceRoots = [path.join(desktopRoot, "src/renderer"), path.join(desktopRoot, "src/main")];
const outputPath = path.join(desktopRoot, "src/renderer/global-copy.generated.ts");

const exact = new Map(Object.entries({
  '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><rect width="32" height="32" rx="8" fill="#5ee0b5"/><text x="16" y="22" text-anchor="middle" font-size="18" font-family="sans-serif" font-weight="700" fill="#07130f">稳</text></svg>': '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><rect width="32" height="32" rx="8" fill="#5ee0b5"/><text x="16" y="22" text-anchor="middle" font-size="18" font-family="sans-serif" font-weight="700" fill="#07130f">O</text></svg>',
  "Default - 当前默认麦克风": "Default microphone",
  "Electron 主助手统一负责麦克风、电脑输出和屏幕采集。": "The Electron companion manages microphone, system audio, and screen capture.",
  "Windows 由主助手统一负责麦克风、电脑输出和屏幕采集。": "On Windows, the companion manages microphone, system audio, and screen capture.",
  "上一笔快捷键截屏仍在处理中，请稍候。": "The previous shortcut capture is still processing. Please wait.",
  "上一笔截屏仍在处理中，请稍候。": "The previous screen capture is still processing. Please wait.",
  "上一笔截屏仍在处理中，请稍后再预览。": "The previous screen capture is still processing. Try previewing again shortly.",
  "上传": "Upload",
  "不支持该快捷键组合，请选择列表中的预设。": "This shortcut is not supported. Choose one of the presets.",
  "仅在已连接并开始面试后生效": "Available after an interview is connected and started",
  "仅用于在本机确认当前捕捉范围，不会因预览自动发送到网页端。": "This preview only confirms the local capture area and is not automatically sent to the web app.",
  "使用固定连接码绑定网页面试": "Use the fixed device code to connect a web interview",
  "使用教程": "Product guide",
  "停止并退出": "Stop and quit",
  "共享屏幕截取": "Shared screen capture",
  "关闭屏幕预览": "Close screen preview",
  "关闭快捷键": "Disable shortcut",
  "关闭快捷键设置": "Close shortcut settings",
  "内建": "Built-in",
  "助手尚未完成服务登记，请检查网络后重试。": "The companion has not registered with the service. Check your network and try again.",
  "助手已从异常退出中恢复，正在重新连接当前面试收音。": "The companion recovered from an unexpected exit and is reconnecting audio for the current interview.",
  "助手设备身份尚未初始化。": "The companion device identity has not been initialised.",
  "助手运行正常": "Companion operating normally",
  "助手连接异常": "Companion connection issue",
  "原生采集流已结束。": "The native capture stream has ended.",
  "原生采集运行时检查失败": "Native capture runtime check failed",
  "原生采集运行时返回了无法解析的事件。": "The native capture runtime returned an unreadable event.",
  "可以开始新的截屏。": "A new screen capture can start.",
  "后端登记失败": "Backend registration failed",
  "复制连接码": "Copy device code",
  "如已在系统设置中授权，请退出并重新打开伴随程序": "If permission is already enabled in System Settings, quit and reopen the companion.",
  "完成": "Done",
  "实时收音链路不稳定，助手正在检查并恢复。": "The realtime audio connection is unstable. The companion is checking and recovering it.",
  "实时收音链路已中断，助手正在自动恢复。": "The realtime audio connection was interrupted. The companion is recovering it automatically.",
  "实时语音已进入后端，并开始同步对话文本": "Realtime audio has reached the service and transcript synchronisation has started.",
  "实时音频授权已失效，需要显式重新连接。": "Realtime audio authorisation has expired. Reconnect the companion.",
  "实时音频顺序已失配，正在自动重建发布链路并从新序列继续。": "Realtime audio sequencing became inconsistent. The publishing connection is rebuilding automatically.",
  "屏幕捕捉": "Screen capture",
  "屏幕缩略图为空，请在系统设置中允许面试稳伴随程序录制屏幕后重启应用。": "The screen preview is empty. Allow screen recording for OfferSteady Companion in System Settings, then restart the app.",
  "屏幕预览 ·": "Screen preview ·",
  "屏幕预览已获取，本地助手可以处理截图回答。": "Screen preview is ready. The companion can process Screenshot Answer requests.",
  "已暂停": "Paused",
  "已绑定 | 等待网页实时连接": "Paired | Waiting for the live web session",
  "已连接": "Connected",
  "已连接 | 网页端已绑定本机": "Connected | Web session paired with this computer",
  "已连接网页端，语音识别正在同步到实时对话": "Connected to the web app. Transcription is syncing to the live conversation.",
  "已连接网页端，音频帧正在持续送入后端实时语音链路": "Connected to the web app. Audio frames are streaming to the realtime service.",
  "当前原生实时采集仅支持 macOS。": "Native realtime capture is currently available only on macOS.",
  "当前截屏已取消，可以重新截屏。": "The current screen capture was cancelled. You can capture again.",
  "当前没有发送新的音频或屏幕数据。": "No new audio or screen data is being sent.",
  "当前没有已连接且正在进行的面试，本次没有截取屏幕。": "No active connected interview was found, so no screen was captured.",
  "当前系统暂不支持桌面采集。": "Desktop capture is not supported on this system yet.",
  "当前选择的屏幕源已经不可用，请在本地助手中重新选择显示器后再试。": "The selected screen is no longer available. Select a display again in the companion.",
  "当前选择的设备不可用，请切换默认设备": "The selected device is unavailable. Switch to the default device.",
  "快捷键": "Shortcut",
  "快捷键已在系统中生效。": "The shortcut is active.",
  "快捷键已触发，正在截取当前选择的屏幕。": "Shortcut triggered. Capturing the selected screen.",
  "快捷键当前未生效，请重新选择。": "The shortcut is not active. Select it again.",
  "快捷键截屏失败，请稍后重试。": "Shortcut screen capture failed. Try again shortly.",
  "快捷键截屏请求缺少任务标识，请稍后重试。": "The shortcut capture request is missing its task ID. Try again shortly.",
  "快捷键未生效：该组合已被系统或其他应用占用，请选择其他组合。": "The shortcut is unavailable because another app or the system is using it. Choose another combination.",
  "快捷键组合": "Shortcut combination",
  "快捷键设置": "Shortcut settings",
  "快捷键设置读取失败，请重启助手。": "Shortcut settings could not be read. Restart the companion.",
  "快捷键设置通道不可用，请重启助手。": "Shortcut settings are unavailable. Restart the companion.",
  "我的声音": "My voice",
  "截屏回答快捷键": "Screenshot Answer shortcut",
  "截屏回答快捷键尚未注册。": "The Screenshot Answer shortcut is not registered.",
  "截屏回答快捷键已关闭。": "The Screenshot Answer shortcut is disabled.",
  "打开伴随程序": "Open companion",
  "打开面试稳网站": "Open OfferSteady website",
  "捕捉屏幕": "Capture screen",
  "收音已就绪": "Audio ready",
  "显示器 1": "Display 1",
  "暂无连接设备": "No connected device",
  "未生效 · 点击设置": "Inactive · Click to configure",
  "未知媒体错误": "Unknown media error",
  "未知错误": "Unknown error",
  "未连接": "Not connected",
  "未连接 | 本机运行信息读取失败，请重新打开伴随程序": "Not connected | Runtime information could not be read. Reopen the companion.",
  "本地助手已完成截图并回传后端。": "The companion captured the screen and sent it to the service.",
  "本地助手心跳过期，正在重新登记这台电脑。": "The companion heartbeat expired. This computer is being registered again.",
  "本地助手执行截图回答失败": "The companion could not complete Screenshot Answer",
  "本地助手未获取到有效共享屏幕画面，请检查屏幕捕捉权限。": "The companion could not capture the shared screen. Check screen-recording permission.",
  "本地网页服务还没启动，请先运行 npm run dev:web，再点击打开。": "The local web service is not running. Start it before opening the website.",
  "本地音频检测启动失败": "Local audio monitoring could not start",
  "本场发布通道已失效，正在等待网页重新连接当前设备。": "The publishing channel expired. Waiting for the web session to reconnect this device.",
  "权限检查失败": "Permission check failed",
  "正在收音": "Listening",
  "正在检查系统权限，机器码和设备身份不会改变…": "Checking system permissions. The device code and identity will not change…",
  "正在生成本机连接码…": "Generating this computer's device code…",
  "正在登记这台电脑…": "Registering this computer…",
  "正在获取最新屏幕画面…": "Getting the latest screen preview…",
  "正在请求屏幕捕捉权限…": "Requesting screen-recording permission…",
  "正在重连": "Reconnecting",
  "没有找到可截取的屏幕，请检查屏幕录制权限。": "No screen is available to capture. Check screen-recording permission.",
  "没有找到可用设备": "No available device was found",
  "没有拿到屏幕视频轨道": "No screen video track was available",
  "没有拿到电脑输出音频轨道；请确认微信、会议或网页面试声音正在这台电脑播放": "No system-audio track was available. Make sure interview audio is playing on this computer.",
  "用户或系统拒绝了权限": "Permission was denied by the user or system",
  "电脑输出": "System audio",
  "电脑输出权限未开启；请在 macOS 系统设置 → 隐私与安全性 → 屏幕与系统音频录制中允许面试稳伴随程序，然后完全退出并重新打开助手": "System-audio permission is disabled. In macOS System Settings → Privacy & Security → Screen & System Audio Recording, allow OfferSteady Companion, then quit and reopen it.",
  "电脑输出权限未开启；请在 macOS 系统设置 → 隐私与安全性 → 屏幕与系统音频录制中允许面试稳伴随程序，然后完全退出并重新打开助手。麦克风收音会继续保持。": "System-audio permission is disabled. In macOS System Settings → Privacy & Security → Screen & System Audio Recording, allow OfferSteady Companion, then quit and reopen it. Microphone capture will continue.",
  "电脑输出没有拿到系统播放音频；请先让面试官声音在这台电脑上实际播放。": "No playing system audio was detected. Make sure the interviewer's audio is playing on this computer.",
  "电脑输出音频": "System audio",
  "窗口标题": "Window title",
  "等待麦克风或电脑输出音频进入实时对话": "Waiting for microphone or system audio to enter the live conversation",
  "系统中断了这次测试": "The system interrupted this test",
  "系统授权与本场连接相互独立，输入固定机器码即可连接面试。": "System permissions are saved independently. Enter the fixed device code to connect an interview.",
  "系统权限已独立保存，等待网页连接本场面试。": "System permissions are saved. Waiting for the web session to connect.",
  "系统权限状态保持不变，请在网页输入固定连接码。": "System permissions remain unchanged. Enter the fixed device code in the web app.",
  "系统没有在限定时间内返回音频流，通常是权限弹窗未处理或屏幕录制权限未开启": "The system did not return an audio stream in time. A permission prompt may be pending or screen recording may be disabled.",
  "系统音频": "System audio",
  "绑定状态查询失败": "Pairing status check failed",
  "缺少 macOS 原生采集运行时，请重新打包安装伴随程序。": "The macOS native capture runtime is missing. Reinstall the companion.",
  "网页未启动：默认检查了本地开发和预览端口": "The web app is not running on the expected local development or preview port.",
  "网页端已绑定本机。": "The web app is paired with this computer.",
  "网页端已请求截图回答，本地助手正在截取当前屏幕。": "The web app requested Screenshot Answer. The companion is capturing the current screen.",
  "网页端绑定已存在，但当前面试页心跳暂未到达；请保持线上实时面试页面打开。": "The device is paired, but the live interview heartbeat has not arrived. Keep the live interview page open.",
  "网页笔试已绑定这台电脑，仅启用截屏回答。": "The written exam is paired with this computer. Only Screenshot Answer is enabled.",
  "网页面试已绑定这台电脑。": "The web interview is paired with this computer.",
  "耳机": "Headphones",
  "获取屏幕源失败，请在系统设置中允许面试稳伴随程序录制屏幕后重启应用。": "Screen sources could not be loaded. Allow screen recording for OfferSteady Companion in System Settings, then restart the app.",
  "设备在线": "Device online",
  "设备在线 | 等待面试连接": "Device online | Waiting for interview connection",
  "设备离线": "Device offline",
  "设备被其他程序占用或系统暂时不可读": "The device is in use by another app or temporarily unavailable",
  "设置截屏回答快捷键": "Configure Screenshot Answer shortcut",
  "识别你的声音": "Transcribe your voice",
  "识别你能听到的面试官声音": "Transcribe interviewer audio played by this computer",
  "语音正在进入后端，等待实时转写同步到网页": "Audio is reaching the service. Waiting for realtime transcription to sync to the web app.",
  "语音识别暂时不可用，正在等待下一段音频": "Transcription is temporarily unavailable. Waiting for the next audio segment.",
  "请保持网页和伴随程序在线。": "Keep the web app and companion online.",
  "请向面试稳伴随程序授予屏幕与系统音频录制权限。": "Allow screen and system-audio recording for OfferSteady Companion.",
  "请在本助手或操作系统隐私设置中完成麦克风与屏幕录制授权。": "Enable microphone and screen-recording permissions in the companion or operating-system privacy settings.",
  "请打开面试首页，进入面试后输入右侧连接码绑定这台电脑。": "Open the interview workspace, then enter the device code shown here to pair this computer.",
  "请检查后端服务、网页连接码或系统授权。": "Check the service, web device code, and system permissions.",
  "输出通道已接入，未检测到播放声音": "System-audio channel connected; no playing audio detected",
  "输出音频": "System audio",
  "这台电脑正在作为面试伴随终端工作。": "This computer is working as the interview companion.",
  "进入并连接正在进行的面试后，即使网页不在前台，也可以直接触发整屏截取和回答。": "After connecting an active interview, use the shortcut to capture the full screen and request an answer even when the web app is not in front.",
  "连接异常": "Connection issue",
  "连接码已复制": "Device code copied",
  "连接码：": "Device code:",
  "连接管理": "Connection",
  "选择屏幕捕捉来源": "Select screen-capture source",
  "选择系统音频": "Select system audio",
  "选择要捕捉的屏幕": "Select the screen to capture",
  "选择麦克风": "Select microphone",
  "通道运行正常": "Channel operating normally",
  "通道需要检查": "Channel needs attention",
  "部分权限尚未开启，请在 Windows 设置 → 隐私和安全性中允许麦克风和屏幕捕捉后重试。": "Some permissions are disabled. In Windows Settings → Privacy & security, allow microphone and screen capture, then try again.",
  "部分权限尚未开启，请在 macOS 系统设置 → 隐私与安全性中允许后重新检查。": "Some permissions are disabled. Enable them in macOS System Settings → Privacy & Security, then check again.",
  "采集链路启动失败": "Capture pipeline could not start",
  "需要权限": "Permission required",
  "需要系统权限": "System permission required",
  "面试官": "Interviewer",
  "面试官声音": "Interviewer audio",
  "面试已开始，本地助手正在启动麦克风、电脑输出和屏幕能力。": "The interview has started. The companion is enabling microphone, system audio, and screen capabilities.",
  "面试稳": "OfferSteady",
  "面试稳伴随助手": "OfferSteady Companion",
  "面试稳伴随程序": "OfferSteady Companion",
  "电脑伴随助手": "Desktop Companion",
  "稳": "O",
  "面试稳首页": "OfferSteady home",
  "音频链路可继续启动，但原生屏幕采集运行时未就绪；不影响语音转写，截屏回答会受影响": "Audio can continue, but the native screen-capture runtime is not ready. Transcription is unaffected; Screenshot Answer may be unavailable.",
  "预览": "Preview",
  "麦克风": "Microphone",
  "麦克风和屏幕录制权限已就绪。": "Microphone and screen-recording permissions are ready.",
  "麦克风和电脑输出都没有成功启动，请检查系统授权和设备选择。": "Neither microphone nor system audio could start. Check system permissions and selected devices.",
  "默认麦克风": "Default microphone",
}));

const templateFragments = new Map(Object.entries({
  " 预览": " preview",
  "。请先打开腾讯会议/微信通话/浏览器面试页面，并确认对方声音正在这台电脑播放。": ". Start audio in the video-call or browser interview and make sure the other person is playing through this computer.",
  "。请在系统设置中允许面试稳伴随程序录制屏幕后重启应用。": ". Allow screen recording for OfferSteady Companion in System Settings, then restart the app.",
  "。请确认后端服务已启动后重试。": ". Confirm the service is available, then try again.",
  "上传连接中断，正在自动恢复。": " upload connection was interrupted and is recovering automatically.",
  "不可用": " unavailable",
  "原生采集流异常退出：": "Native capture stream exited unexpectedly: ",
  "启动失败：": " could not start: ",
  "实时音频授权已失效，请退出当前面试并重新连接助手：": "Realtime audio authorisation expired. Leave the current interview and reconnect the companion: ",
  "实时音频连接失败，请重新连接助手后再开始面试：": "Realtime audio connection failed. Reconnect the companion before starting the interview: ",
  "屏幕捕捉已就绪：": "Screen capture ready: ",
  "屏幕捕捉预览失败：": "Screen preview failed: ",
  "已绑定面试：": "Paired interview: ",
  "已采集，但实时传输通道建立失败，请检查后端 WebSocket 是否可用。": " was captured, but the realtime transport could not connect. Check WebSocket availability.",
  "当前系统不支持": " is not supported on this system",
  "快捷键截屏请求失败：": "Shortcut capture request failed: ",
  "截图上传失败：": "Screen capture upload failed: ",
  "截图失败：": "Screen capture failed: ",
  "收音正常 ": " receiving audio ",
  "显示器 ": "Display ",
  "未授权": " permission not granted",
  "权限检查失败：": "Permission check failed: ",
  "权限被系统拒绝，请在系统设置中授权后重试。": " permission was denied. Enable it in System Settings and try again.",
  "检测失败：": " monitoring failed: ",
  "检测异常": " monitoring issue",
  "登记失败：": "Registration failed: ",
  "等待声音": " waiting for audio",
  "等待检测": " waiting for check",
  "绑定查询失败：": "Pairing check failed: ",
  "自动恢复失败，请在助手中重新开始面试。": " automatic recovery failed. Restart the interview in the companion.",
  "获取屏幕源失败：": "Could not load screen source: ",
  "还没成功接入后端发布链路，请检查本地后端服务和当前面试是否已开始。": " has not connected to the publishing service. Check service availability and whether the interview has started.",
  "选择要捕捉的屏幕：": "Selected screen: ",
  "重连中": " reconnecting",
  "需要系统音频适配器": " requires a system-audio adapter",
  "音量条": " level meter",
  "麦克风 ": "Microphone ",
  "，等待网页端点击开始面试": ", waiting for the interview to be started in the web app",
}));

const hashText = value => {
  let hash = 0x811c9dc5;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(36);
};
const translate = source => {
  const normalized = source.trim().replace(/\s+/g, " ");
  return exact.get(normalized);
};

const values = new Set();
const fragments = new Set();
const collect = directory => {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const filePath = path.join(directory, entry.name);
    if (entry.isDirectory()) collect(filePath);
    if (!entry.isFile() || !/\.(ts|tsx)$/.test(entry.name) || entry.name.includes(".test.") || filePath === outputPath) continue;
    const content = fs.readFileSync(filePath, "utf8");
    const sourceFile = ts.createSourceFile(filePath, content, ts.ScriptTarget.Latest, true, entry.name.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
    const visit = node => {
      if ((ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node) || ts.isJsxText(node)) && /[\u3400-\u9fff]/.test(node.text)) {
        const normalized = node.text.trim().replace(/\s+/g, " ");
        if (normalized) values.add(normalized);
      }
      if (ts.isTemplateExpression(node)) {
        for (const part of [node.head.text, ...node.templateSpans.map(span => span.literal.text)]) {
          if (/[\u3400-\u9fff]/.test(part)) fragments.add(part);
        }
      }
      ts.forEachChild(node, visit);
    };
    visit(sourceFile);
  }
};
sourceRoots.forEach(collect);
const missingValues = [...values].sort().filter(value => !exact.has(value));
const missingFragments = [...fragments].sort().filter(value => !templateFragments.has(value));
if (missingValues.length || missingFragments.length) {
  const detail = [
    ...missingValues.map(value => `Missing exact translation: ${JSON.stringify(value)}`),
    ...missingFragments.map(value => `Missing template translation: ${JSON.stringify(value)}`),
  ].join("\n");
  throw new Error(`Global companion copy is incomplete. Add explicit translations before building:\n${detail}`);
}
const copy = Object.fromEntries([...values].sort().map(value => [hashText(value), translate(value)]));
const replacementSources = new Map([...exact, ...templateFragments]);
const replacementFragments = Object.fromEntries(
  [...replacementSources]
    .sort(([left], [right]) => right.length - left.length)
    .map(([source, target]) => [Buffer.from(source, "utf8").toString("base64"), target]),
);
fs.writeFileSync(outputPath, `// Generated by scripts/generate-global-companion-copy.mjs.\nexport const globalCompanionCopyByHash: Readonly<Record<string, string>> = ${JSON.stringify(copy, null, 2)};\nexport const globalCompanionCopyFragments: Readonly<Record<string, string>> = ${JSON.stringify(replacementFragments, null, 2)};\n`);
console.log(`Generated ${values.size} exact and ${replacementFragments ? Object.keys(replacementFragments).length : 0} composable Global companion copy entries.`);
