import type { GuideContent } from "@offersteady/protocol";

export const guideContent: GuideContent = {
  version: "1.0.0-global",
  locale: "en-US",
  chapters: [
    {
      id: "quick-start",
      title: "Quick start",
      keywords: ["start", "account", "interview", "written exam"],
      summary: "Set up your account, companion app, and first session.",
      sections: [{
        id: "steps",
        title: "Start in five steps",
        paragraphs: [
          "Sign in, then choose Interview Mode or Written Exam Mode from the workspace navigation.",
          "For an interview, add only the resume, job description, and reference materials you want the assistant to use. You may also continue without materials.",
          "Install the Global companion build for your operating system and enter its six-digit connection code on the preparation page.",
          "Confirm the session language, coding preference, and selected materials before entering the live workspace.",
          "Grant microphone, system-audio, and screen-capture access only when you use the corresponding feature.",
        ],
      }],
    },
    {
      id: "account-library",
      title: "Account and materials",
      keywords: ["sign in", "resume", "job description", "knowledge", "library"],
      summary: "Manage reusable interview context without sharing it with every session.",
      sections: [
        {
          id: "account",
          title: "Account access",
          paragraphs: ["The Global deployment will use its own identity service and data store. Accounts and sessions will not be shared with the domestic product."],
        },
        {
          id: "library",
          title: "Resume, job description, and knowledge",
          paragraphs: [
            "Materials are grouped by type. Adding an item does not automatically attach it to an interview; select the required items for each session on the preparation page.",
            "Avoid uploading secrets or information you are not permitted to share. Delete obsolete materials from the library when they are no longer needed.",
          ],
        },
      ],
    },
    {
      id: "desktop",
      title: "Companion app",
      keywords: ["Windows", "macOS", "microphone", "system audio", "screen capture"],
      summary: "Connect the companion app and verify device permissions.",
      sections: [
        {
          id: "install",
          title: "Install the correct build",
          paragraphs: ["Use the Global Windows x64, macOS Apple silicon, or macOS Intel package that matches your device. Global and domestic builds have separate identities and local data directories."],
        },
        {
          id: "permissions",
          title: "Permissions and recovery",
          paragraphs: [
            "Microphone audio is labelled as You. System audio is labelled as Interviewer. Screen capture is requested only when you trigger a screenshot answer.",
            "If a device changes during a session, reconnect it in the companion app. Manual questions and screenshot answers remain available when an audio source is temporarily unavailable.",
          ],
        },
      ],
    },
    {
      id: "live",
      title: "Live interview",
      keywords: ["transcript", "quick answer", "automatic answer", "screenshot"],
      summary: "Follow the transcript and control when an answer is generated.",
      sections: [
        {
          id: "conversation",
          title: "Conversation and answers",
          paragraphs: [
            "The live transcript keeps your microphone and interviewer system audio separate. Partial speech may be revised while recognition is still in progress; confirmed transcript history should remain stable.",
            "Quick Answer uses a manually entered question first. Otherwise it uses the most recent interviewer question after your latest response. Automatic Answer is off by default and can be enabled for the current session.",
            "Stopping an answer cancels only the current generation. It does not end audio capture or the interview session.",
          ],
        },
        {
          id: "screenshot",
          title: "Screenshot answers",
          paragraphs: ["Screenshot Answer captures the selected display only after you request it. A failed or cancelled capture can be retried and is not silently submitted."],
        },
      ],
    },
    {
      id: "written-exam",
      title: "Written exam mode",
      keywords: ["written exam", "coding", "screenshot answer"],
      summary: "Use screenshot answers without starting the interview audio pipeline.",
      sections: [{
        id: "workflow",
        title: "Written exam workflow",
        paragraphs: [
          "Written Exam Mode connects the companion app but does not start microphone or system-audio transcription. Submit a screenshot when you want help with a question.",
          "If coding assistance is enabled, the response follows the programming language selected before the session. Existing results remain visible until you replace or close them.",
        ],
      }],
    },
    {
      id: "billing",
      title: "Plans and billing",
      keywords: ["plan", "billing", "credits", "payment"],
      summary: "Global commerce remains unavailable until the regional provider is configured.",
      sections: [{
        id: "availability",
        title: "Regional availability",
        paragraphs: [
          "Prices, currency, taxes, payment methods, refunds, and plan terms will be published for the selected launch market before Global commerce is enabled.",
          "The development build intentionally does not route Global purchases through domestic payment providers.",
        ],
      }],
    },
    {
      id: "privacy-support",
      title: "Privacy and support",
      keywords: ["privacy", "delete", "support", "security"],
      summary: "Understand data controls and request help safely.",
      sections: [{
        id: "privacy",
        title: "Data controls",
        paragraphs: [
          "Raw interview audio is not stored by default. The Global deployment will define its own regional retention, deletion, and subprocessors before launch.",
          "Never send passwords, one-time codes, full payment credentials, or identity documents in a support request.",
        ],
      }],
    },
  ],
};

export const safeGuideContent = (content: GuideContent) => {
  const unsafe = /<script|<iframe|javascript:/i;
  if (content.chapters.some((chapter) => unsafe.test(JSON.stringify(chapter)))) {
    throw new Error("unsafe-guide-content");
  }
  return content;
};
