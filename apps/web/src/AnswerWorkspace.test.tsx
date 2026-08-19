import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AnswerWorkspace } from "./AnswerWorkspace";
import { syntheticState } from "./test-state";

describe("AnswerWorkspace", () => {
  it("keeps question normalization metadata internal while the answer streams", () => {
    const question = {
      ...syntheticState.questions[0]!,
      status: "streaming" as const,
      questionNormalizationStatus: "pending" as const,
    };
    const props = {
      answers: [question],
      viewingAnswerId: null,
      newAnswerAvailable: false,
      activeTask: null,
      cancelling: false,
      cancelError: "",
      onView: () => undefined,
      onRetry: () => undefined,
      onStop: () => undefined,
    };
    const { rerender } = render(<AnswerWorkspace {...props} />);

    expect(screen.getByText(question.text)).toBeInTheDocument();
    expect(screen.queryByText("正在整理面试官的问题")).not.toBeInTheDocument();

    rerender(<AnswerWorkspace {...props} answers={[{ ...question, questionNormalizationStatus: "completed" }]} />);

    expect(screen.getByText(question.text)).toBeInTheDocument();
    expect(screen.queryByText("AI 整理的问题")).not.toBeInTheDocument();
    expect(screen.queryByText("根据当前转录识别的问题")).not.toBeInTheDocument();
  });

  it("uses stable text while streaming and formats markdown only after completion", () => {
    const question = {
      ...syntheticState.questions[0]!,
      status: "streaming" as const,
      advice: { ...syntheticState.questions[0]!.advice, detail: "**稳定显示的回答**" },
    };
    const activeTask = {
      id: "answer-task",
      interviewId: "demo",
      userId: "synthetic-user",
      billingUsageId: "synthetic-usage",
      questionId: question.id,
      revision: 1,
      status: "generating" as const,
      question: question.text,
      partialText: question.advice.detail,
      updatedAtMs: 1,
    };
    const props = {
      answers: [question],
      viewingAnswerId: null,
      newAnswerAvailable: false,
      activeTask,
      cancelling: false,
      cancelError: "",
      onView: () => undefined,
      onRetry: () => undefined,
      onStop: () => undefined,
    };
    const { container, rerender } = render(<AnswerWorkspace {...props} />);

    expect(container.querySelector(".answer-stream-text")).toHaveTextContent("**稳定显示的回答**");
    expect(container.querySelector(".answer-markdown strong")).not.toBeInTheDocument();

    rerender(<AnswerWorkspace {...props} answers={[{ ...question, status: "confirmed" }]} activeTask={null} />);

    expect(container.querySelector(".answer-stream-text")).not.toBeInTheDocument();
    expect(container.querySelector(".answer-markdown strong")).toHaveTextContent("稳定显示的回答");
  });
});
