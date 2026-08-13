import type {
  InterviewQuestion,
  InterviewReview,
  InterviewSummary,
} from "./domain";

const MIME_TYPE =
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
const INCH = 1440;
const COLORS = {
  ink: "172033",
  accent: "087F6B",
  interviewer: "2563EB",
  candidate: "087F6B",
  muted: "667085",
  soft: "EEF8F5",
  line: "D9E4E1",
};

const safeLine = (value: string) => value.replace(/\r?\n/g, " ").trim();
const formatDateTime = (value?: number | null) => {
  if (!value) return "未记录";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "未记录";
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date);
};

export const interviewReviewWordFilename = (
  title: string,
  endedAtMs?: number | null,
) => {
  const date = endedAtMs ? new Date(endedAtMs) : new Date();
  const stamp = Number.isNaN(date.getTime())
    ? "unknown-date"
    : date.toISOString().slice(0, 10);
  const safeTitle =
    safeLine(title)
      .replace(/[\\/:*?"<>|]/g, "-")
      .replace(/\s+/g, "-")
      .slice(0, 60) || "面试复盘";
  return `${safeTitle}-${stamp}.docx`;
};

const sourceLabel = (question: InterviewQuestion) =>
  question.input === "screenshot"
    ? "截图题"
    : question.input === "manual"
      ? "手动输入"
      : "音频转写";

export async function createInterviewReviewWordBlob(
  review: InterviewReview,
  questions: readonly InterviewQuestion[],
  interview?: InterviewSummary,
): Promise<Blob> {
  const {
    AlignmentType,
    BorderStyle,
    Document,
    Footer,
    HeadingLevel,
    PageNumber,
    Packer,
    Paragraph,
    ShadingType,
    TextRun,
  } = await import("docx");

  const title = review.title || interview?.title || "本场面试复盘";
  const bodyParagraph = (text: string, options?: { bold?: boolean }) =>
    new Paragraph({
      spacing: { after: 120, line: 276 },
      children: [
        new TextRun({
          text,
          ...(options?.bold ? { bold: true } : {}),
          size: 21,
          color: COLORS.ink,
          font: "Microsoft YaHei",
        }),
      ],
    });
  const metadataParagraph = (label: string, value: string) =>
    new Paragraph({
      spacing: { after: 70, line: 260 },
      children: [
        new TextRun({
          text: `${label}：`,
          bold: true,
          size: 20,
          color: COLORS.muted,
          font: "Microsoft YaHei",
        }),
        new TextRun({
          text: value,
          size: 20,
          color: COLORS.ink,
          font: "Microsoft YaHei",
        }),
      ],
    });
  const sectionHeading = (text: string) =>
    new Paragraph({
      heading: HeadingLevel.HEADING_1,
      keepNext: true,
      children: [new TextRun({ text, font: "Microsoft YaHei" })],
    });

  const transcriptChildren = review.transcripts.length
    ? review.transcripts.flatMap(item => [
        new Paragraph({
          keepNext: true,
          spacing: { before: 100, after: 45 },
          children: [
            new TextRun({
              text: item.speakerLabel,
              bold: true,
              size: 21,
              color:
                item.role === "interviewer"
                  ? COLORS.interviewer
                  : COLORS.candidate,
              font: "Microsoft YaHei",
            }),
            new TextRun({
              text: `  ${formatDateTime(item.occurredAtMs)}`,
              size: 18,
              color: COLORS.muted,
              font: "Microsoft YaHei",
            }),
          ],
        }),
        bodyParagraph(item.text.trim()),
      ])
    : [bodyParagraph("本场没有可用的持久语音转写。")];

  const orderedQuestions = [...questions].reverse();
  const questionChildren = orderedQuestions.length
    ? orderedQuestions.flatMap((question, index) => {
        const children = [
          new Paragraph({
            heading: HeadingLevel.HEADING_2,
            keepNext: true,
            children: [
              new TextRun({
                text: `${index + 1}. ${safeLine(question.text)}`,
                font: "Microsoft YaHei",
              }),
            ],
          }),
          new Paragraph({
            spacing: { after: 100 },
            children: [
              new TextRun({
                text: `${question.askedAt} · ${sourceLabel(question)}`,
                size: 18,
                color: COLORS.muted,
                font: "Microsoft YaHei",
              }),
            ],
          }),
          new Paragraph({
            keepNext: true,
            spacing: { before: 60, after: 60 },
            children: [
              new TextRun({
                text: "AI 回答建议",
                bold: true,
                size: 20,
                color: COLORS.accent,
                font: "Microsoft YaHei",
              }),
            ],
          }),
        ];
        if (question.advice.outline.length) {
          question.advice.outline.forEach(item => {
            children.push(
              new Paragraph({
                bullet: { level: 0 },
                spacing: { after: 70, line: 276 },
                children: [
                  new TextRun({
                    text: safeLine(item),
                    size: 21,
                    color: COLORS.ink,
                    font: "Microsoft YaHei",
                  }),
                ],
              }),
            );
          });
        }
        const detail = question.advice.detail.trim();
        if (detail) {
          detail.split(/\n{2,}/).forEach(paragraph => {
            children.push(bodyParagraph(paragraph.trim()));
          });
        } else if (!question.advice.outline.length) {
          children.push(bodyParagraph("暂无 AI 回答建议。"));
        }
        return children;
      })
    : [bodyParagraph("本场没有已保存的问题与 AI 回答建议。")];

  const document = new Document({
    creator: "面试稳AI助手",
    title: `${title} - 面试复盘`,
    description: "由用户主动下载的本地面试复盘文档",
    styles: {
      default: {
        document: {
          run: {
            font: "Microsoft YaHei",
            size: 21,
            color: COLORS.ink,
          },
          paragraph: { spacing: { after: 120, line: 276 } },
        },
      },
      paragraphStyles: [
        {
          id: "ReviewTitle",
          name: "Review Title",
          basedOn: "Normal",
          next: "Normal",
          quickFormat: true,
          run: {
            bold: true,
            size: 34,
            color: COLORS.ink,
            font: "Microsoft YaHei",
          },
          paragraph: { spacing: { after: 130 } },
        },
        {
          id: "Heading1",
          name: "Heading 1",
          basedOn: "Normal",
          next: "Normal",
          quickFormat: true,
          run: {
            bold: true,
            size: 28,
            color: COLORS.accent,
            font: "Microsoft YaHei",
          },
          paragraph: {
            spacing: { before: 300, after: 130 },
            border: {
              bottom: {
                color: COLORS.line,
                style: BorderStyle.SINGLE,
                size: 6,
                space: 6,
              },
            },
          },
        },
        {
          id: "Heading2",
          name: "Heading 2",
          basedOn: "Normal",
          next: "Normal",
          quickFormat: true,
          run: {
            bold: true,
            size: 23,
            color: COLORS.ink,
            font: "Microsoft YaHei",
          },
          paragraph: { spacing: { before: 220, after: 80 } },
        },
      ],
    },
    numbering: {
      config: [
        {
          reference: "review-bullets",
          levels: [
            {
              level: 0,
              format: "bullet",
              text: "•",
              alignment: AlignmentType.LEFT,
              style: {
                paragraph: {
                  indent: { left: 600, hanging: 260 },
                  spacing: { after: 70, line: 276 },
                },
              },
            },
          ],
        },
      ],
    },
    sections: [
      {
        properties: {
          page: {
            size: { width: Math.round(8.27 * INCH), height: Math.round(11.69 * INCH) },
            margin: {
              top: Math.round(0.85 * INCH),
              right: Math.round(0.9 * INCH),
              bottom: Math.round(0.8 * INCH),
              left: Math.round(0.9 * INCH),
              footer: Math.round(0.42 * INCH),
            },
          },
        },
        footers: {
          default: new Footer({
            children: [
              new Paragraph({
                alignment: AlignmentType.RIGHT,
                children: [
                  new TextRun({
                    text: "面试稳AI助手 · 面试复盘  |  ",
                    size: 17,
                    color: COLORS.muted,
                    font: "Microsoft YaHei",
                  }),
                  new TextRun({
                    children: [PageNumber.CURRENT],
                    size: 17,
                    color: COLORS.muted,
                    font: "Microsoft YaHei",
                  }),
                ],
              }),
            ],
          }),
        },
        children: [
          new Paragraph({
            style: "ReviewTitle",
            children: [new TextRun({ text: title, font: "Microsoft YaHei" })],
          }),
          new Paragraph({
            spacing: { after: 230 },
            shading: { type: ShadingType.CLEAR, fill: COLORS.soft },
            border: {
              left: {
                color: COLORS.accent,
                style: BorderStyle.SINGLE,
                size: 16,
                space: 8,
              },
            },
            children: [
              new TextRun({
                text: "面试复盘 · 语音转写与 AI 回答建议",
                bold: true,
                size: 21,
                color: COLORS.accent,
                font: "Microsoft YaHei",
              }),
            ],
          }),
          metadataParagraph("开始时间", formatDateTime(review.startedAtMs)),
          metadataParagraph("结束时间", formatDateTime(review.endedAtMs)),
          metadataParagraph("面试时长", review.duration),
          new Paragraph({
            spacing: { before: 100, after: 120, line: 260 },
            children: [
              new TextRun({
                text: "说明：对话内容来自语音转写，可能存在识别误差；AI 回答建议不代表候选人实际说法。",
                italics: true,
                size: 18,
                color: COLORS.muted,
                font: "Microsoft YaHei",
              }),
            ],
          }),
          sectionHeading("真实对话记录（语音转写）"),
          ...transcriptChildren,
          sectionHeading("问题与 AI 回答建议"),
          ...questionChildren,
        ],
      },
    ],
  });

  return Packer.toBlob(document);
}

export function downloadInterviewReviewWord(filename: string, blob: Blob) {
  const normalized =
    blob.type === MIME_TYPE ? blob : new Blob([blob], { type: MIME_TYPE });
  const url = URL.createObjectURL(normalized);
  try {
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.style.display = "none";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  } finally {
    URL.revokeObjectURL(url);
  }
}
