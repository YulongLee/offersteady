import type { MockSession } from "./mock-interview-client";
import { mockReportDimensionLabels, mockReportDisclosure } from "./mock-interview-report";
import { downloadInterviewReviewWord } from "./interview-review-word-export";

// Keep user text literal and editable; exclude characters forbidden by XML 1.0.
const xmlText = (text: string) => text.replace(/[^\u0009\u000A\u000D\u0020-\uD7FF\uE000-\uFFFD\u{10000}-\u{10FFFF}]/gu, "");

export function mockInterviewWordFilename(title: string): string {
  const safeTitle = Array.from(xmlText(title)
    .replace(/[\\/:*?"<>|\u007f-\u009f\u200e\u200f\u202a-\u202e\u2066-\u2069]/g, "-")
    .replace(/\s+/g, " ").replace(/^[. ]+|[. ]+$/g, "")).slice(0, 60).join("").trim();
  return `模拟面试报告${safeTitle ? `-${safeTitle}` : ""}.docx`;
}

export async function createMockInterviewWordBlob(session: MockSession): Promise<Blob> {
  if (session.state.phase !== "completed" || !session.report) {
    throw new Error("报告尚未生成完成，请稍后再试。");
  }
  const report = session.report;
  const { Document, Footer, HeadingLevel, PageNumber, Packer, Paragraph, TextRun, AlignmentType } = await import("docx");
  const font = { ascii: "Arial", hAnsi: "Arial", eastAsia: "Microsoft YaHei", cs: "Arial" };
  const body = (text: string, bold = false, keepNext = false) => xmlText(text).split(/\r\n|\r|\n/).map(line => new Paragraph({
    keepNext,
    children: [new TextRun({ text: line, bold })],
  }));
  const heading = (text: string, level: typeof HeadingLevel.HEADING_1 | typeof HeadingLevel.HEADING_2 = HeadingLevel.HEADING_1) => new Paragraph({
    text, heading: level, keepNext: true,
  });
  const labeled = (label: string, text: string) => [
    new Paragraph({ keepNext: true, spacing: { before: 100, after: 40 }, children: [new TextRun({ text: label, bold: true })] }),
    ...body(text),
  ];
  const document = new Document({
    creator: "面试稳", title: "模拟面试报告", description: "模拟面试练习反馈与逐题问答",
    styles: {
      default: { document: {
        run: { font, size: 22, color: "000000" },
        paragraph: { spacing: { after: 80, line: 288 } },
      } },
      paragraphStyles: [
        { id: "Title", name: "Title", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { font, size: 44, bold: true, color: "000000" }, paragraph: { spacing: { after: 240 }, keepNext: true } },
        { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { font, size: 28, bold: true, color: "000000" }, paragraph: { spacing: { before: 220, after: 100 }, keepNext: true } },
        { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { font, size: 24, bold: true, color: "000000" }, paragraph: { spacing: { before: 180, after: 80 }, keepNext: true } },
      ],
    },
    sections: [{
      properties: { page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1152, bottom: 1152, left: 1152, right: 1152, footer: 576 },
      } },
      footers: { default: new Footer({ children: [new Paragraph({
        alignment: AlignmentType.RIGHT,
        children: [new TextRun({ children: [PageNumber.CURRENT], size: 18, color: "666666" })],
      })] }) },
      children: [
        new Paragraph({ text: "模拟面试报告", heading: HeadingLevel.TITLE }),
        ...body(`场次名称：${session.title || "模拟面试"}`),
        ...body(`目标岗位：${session.targetRole || "未指定"}`),
        ...body(session.partial ? "部分练习报告" : "完整练习报告", true),
        ...body(mockReportDisclosure),
        heading("总体评价"),
        ...body(report.overall_score == null ? "有效回答不足，不评分" : `总体评分：${report.overall_score} / 100`, true),
        ...body(report.summary),
        ...(report.dimensions && Object.keys(report.dimensions).length ? [
          heading("分项评分"),
          ...Object.entries(report.dimensions).flatMap((_, index, entries) => index % 2 ? [] : body(
            entries.slice(index, index + 2).map(([name, value]) => `${mockReportDimensionLabels[name] ?? name}：${value} / 100`).join("    "),
          )),
        ] : []),
        heading("逐题复盘"),
        ...(session.state.rounds.length ? session.state.rounds.flatMap((round, index) => {
          const answered = Boolean(round.answer?.trim());
          const feedback = answered ? report.feedback.find(item => item.question_id === round.question_id) : undefined;
          return [
            heading(`第 ${index + 1} 题`, HeadingLevel.HEADING_2),
            ...body(round.question, true),
            ...labeled("你的回答", answered ? round.answer! : "本题未提交回答，不计分。"),
            ...(feedback ? [
              ...labeled("回答中的证据", feedback.answer_quote),
              ...labeled("做得好的地方", feedback.strength),
              ...labeled("可以提升", feedback.improvement),
              ...labeled("回答建议", feedback.suggestion),
            ] : answered ? body("本题暂无逐题反馈。") : []),
          ];
        }) : body("本场没有已发布的问题。")),
        ...(report.practice_priorities.length ? [
          heading("下一次练习重点"),
          ...report.practice_priorities.flatMap((tip, index) => body(`${index + 1}. ${tip}`, false, index < report.practice_priorities.length - 1)),
        ] : []),
      ],
    }],
  });
  return Packer.toBlob(document);
}

export async function downloadMockInterviewWord(session: MockSession): Promise<void> {
  const blob = await createMockInterviewWordBlob(session);
  downloadInterviewReviewWord(mockInterviewWordFilename(session.title), blob);
}
