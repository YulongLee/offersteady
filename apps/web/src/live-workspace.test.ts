import { describe, expect, it } from "vitest";
import { syntheticState } from "./test-state";
import { DEFAULT_SPLIT_RATIO, answerPage, clampSplitRatio, initialLiveWorkspaceView, isolateRealtimeSpeakerSession, mergeAnswerTask, noteNewAnswer, parseStoredSplitRatio, reconcileAnswerWorkspace, reconcileRealtimeSpeaker, resetTransientInterviewState, serializeSplitRatio, splitRatioBounds, splitRatioStorageKey } from "./live-workspace";

describe("live workspace answer pagination", () => {
  const answers = syntheticState.questions;

  it("moves through stable answer ids and disables boundary directions", () => {
    const latest = answerPage(answers, null)!;
    expect(latest.answer.id).toBe("q-current");
    expect(latest.nextId).toBeNull();
    expect(latest.previousId).toBe("q-old");

    const oldest = answerPage(answers, "q-old")!;
    expect(oldest.answer.id).toBe("q-old");
    expect(oldest.previousId).toBeNull();
    expect(oldest.nextId).toBe("q-current");
  });

  it("keeps the selected historical id when a new answer arrives", () => {
    const browsing = { ...initialLiveWorkspaceView(), viewingAnswerId: "q-old" };
    const updated = noteNewAnswer(browsing, "q-current", "q-new");
    expect(updated.viewingAnswerId).toBe("q-old");
    expect(updated.newAnswerAvailable).toBe(true);
  });

  it("validates, clamps and versions session-scoped split ratios", () => {
    expect(splitRatioStorageKey("session-a")).not.toBe(splitRatioStorageKey("session-b"));
    expect(parseStoredSplitRatio(serializeSplitRatio(57))).toBe(57);
    expect(parseStoredSplitRatio('{"version":0,"ratio":57}')).toBe(DEFAULT_SPLIT_RATIO);
    expect(parseStoredSplitRatio('{"version":1,"ratio":999}')).toBe(DEFAULT_SPLIT_RATIO);
    expect(parseStoredSplitRatio("broken")).toBe(DEFAULT_SPLIT_RATIO);
    expect(clampSplitRatio(10)).toBe(25);
    expect(clampSplitRatio(90)).toBe(75);
  });

  it("derives minimum-width bounds from the available desktop width", () => {
    const bounds = splitRatioBounds(1200);
    expect(bounds.min).toBeGreaterThanOrEqual(25);
    expect(bounds.max).toBeLessThanOrEqual(75);
    expect(clampSplitRatio(5, bounds)).toBe(bounds.min);
    expect(clampSplitRatio(95, bounds)).toBe(bounds.max);
  });

  it("keeps the newest revision metadata without accepting a stable-prefix rewrite", () => {
    const current = syntheticState.speaker;
    const original = current.transcripts[0]!;
    const reconciled = reconcileRealtimeSpeaker(current, {
      ...current,
      transcripts: [
        { ...original, revision: original.revision + 1, text: "更新后的实时文本", isFinal: false },
        { ...original, revision: original.revision + 2, text: "最终实时文本", isFinal: true },
        { ...original, id: "blank-segment", text: "   ", revision: 1 },
      ],
    });
    expect(reconciled.transcripts.filter(segment => segment.id === original.id)).toEqual([
      expect.objectContaining({ revision: original.revision + 2, text: original.text, isFinal: true }),
    ]);
    expect(reconciled.transcripts.some(segment => segment.id === "blank-segment")).toBe(false);
  });

  it("allows bounded tail correction but blocks a longer rewrite before the stable prefix", () => {
    const original = {
      ...syntheticState.speaker.transcripts[0]!,
      text: "请介绍一下你在上一家公司负责的核心项目上线",
      revision: 4,
      isFinal: false,
    };
    const tailCorrection = {
      ...original,
      text: "请介绍一下你在上一家公司负责的核心项目复盘结果",
      revision: 5,
    };
    const corrected = reconcileRealtimeSpeaker(
      { ...syntheticState.speaker, transcripts: [original] },
      { ...syntheticState.speaker, transcripts: [tailCorrection] },
    );
    expect(corrected.transcripts[0]).toMatchObject({ revision: 5, text: tailCorrection.text });

    const destructive = {
      ...tailCorrection,
      text: `能否重新改写${tailCorrection.text}并追加内容`,
      revision: 6,
      isFinal: true,
    };
    const frozen = reconcileRealtimeSpeaker(corrected, {
      ...syntheticState.speaker,
      transcripts: [destructive],
    });
    expect(frozen.transcripts[0]).toMatchObject({ revision: 6, text: tailCorrection.text, isFinal: true });
  });

  it("does not let a stale snapshot overwrite a newer partial revision", () => {
    const current = syntheticState.speaker;
    const original = current.transcripts[0]!;
    const newer = { ...original, revision: original.revision + 3, text: "本地已收到的新版本" };
    const reconciled = reconcileRealtimeSpeaker(
      { ...current, transcripts: [newer] },
      { ...current, transcripts: [original] },
    );
    expect(reconciled.transcripts).toEqual([newer]);
  });

  it("keeps an incomplete recovery terminal when a later partial is replayed", () => {
    const original = syntheticState.speaker.transcripts[0]!;
    const incomplete = { ...original, revision: 4, isFinal: true, terminalState: "incomplete" as const, text: "可见但未完整的文本" };
    const replayedPartial = { ...original, revision: 5, isFinal: false, text: "迟到局部结果" };
    const reconciled = reconcileRealtimeSpeaker(
      { ...syntheticState.speaker, transcripts: [incomplete] },
      { ...syntheticState.speaker, transcripts: [replayedPartial] },
    );
    expect(reconciled.transcripts).toEqual([incomplete]);
  });

  it("keeps a newer turn visible when an older turn finalizes late", () => {
    const original = syntheticState.speaker.transcripts[0]!;
    const olderFinal = { ...original, id: "older", revision: 4, isFinal: true, text: "较早问题最终稿", startedAtMs: 100, endedAtMs: 800 };
    const newerPartial = { ...original, id: "newer", revision: 2, isFinal: false, text: "新的问题正在显示", startedAtMs: 900, endedAtMs: 1_200 };
    const reconciled = reconcileRealtimeSpeaker(
      { ...syntheticState.speaker, transcripts: [newerPartial] },
      { ...syntheticState.speaker, transcripts: [olderFinal, newerPartial] },
    );

    expect(reconciled.transcripts).toEqual([olderFinal, newerPartial]);
  });

  it("drops realtime content from another interview session instead of merging it", () => {
    const current = syntheticState.speaker;
    const incoming = {
      ...current,
      transcripts: [],
      pendingQuestion: null,
      runtimeNotice: { stage: "waiting-audio", message: "等待新面试的实时语音" },
    };
    const isolated = isolateRealtimeSpeakerSession(current, "new-session");
    const reconciled = reconcileRealtimeSpeaker(current, incoming, "new-session");

    expect(isolated.transcripts).toEqual([]);
    expect(isolated.pendingQuestion).toBeNull();
    expect(reconciled.transcripts).toEqual([]);
    expect(reconciled.pendingQuestion).toBeNull();
    expect(reconciled.runtimeNotice?.message).toBe("等待新面试的实时语音");
  });

  it("resets transient conversation and answer state for a newly created interview", () => {
    const reset = resetTransientInterviewState(syntheticState);

    expect(reset.interviews).toEqual(syntheticState.interviews);
    expect(reset.questions).toEqual([]);
    expect(reset.speaker.transcripts).toEqual([]);
    expect(reset.speaker.pendingQuestion).toBeNull();
    expect(reset.activeAnswerTask).toBeNull();
    expect(reset.captureState).toBe("ready");
  });

  it("does not let an older task or shorter stream update replace current content", () => {
    const current = {
      id: "answer-new", interviewId: "demo", userId: "synthetic-user", billingUsageId: "usage-new",
      questionId: "q-current", question: "新的合成问题", revision: 3, status: "completed" as const,
      partialText: "已经显示的完整合成回答", completedText: "已经显示的完整合成回答", updatedAtMs: 300,
    };
    const { completedText: _completedText, ...currentWithoutCompleted } = current;
    const stale = { ...currentWithoutCompleted, revision: 2, status: "generating" as const, partialText: "较短回答", updatedAtMs: 200 };
    expect(mergeAnswerTask(current, stale)).toMatchObject({ status: "completed", partialText: "已经显示的完整合成回答", completedText: "已经显示的完整合成回答" });
  });

  it("keeps a newer local answer current when an older history snapshot arrives", () => {
    const currentQuestion = syntheticState.questions[0]!;
    const oldQuestion = syntheticState.questions[1]!;
    const currentTask = {
      id: "answer-new", interviewId: "demo", userId: "synthetic-user", billingUsageId: "usage-new",
      questionId: currentQuestion.id, question: currentQuestion.text, revision: 1, status: "generating" as const,
      partialText: "正在生成新的合成回答", updatedAtMs: 300,
    };
    const oldTask = { ...currentTask, id: "answer-old", questionId: oldQuestion.id, question: oldQuestion.text, status: "completed" as const, updatedAtMs: 200 };
    const reconciled = reconcileAnswerWorkspace(
      { questions: [currentQuestion], activeAnswerTask: currentTask },
      { questions: [oldQuestion], activeAnswerTask: oldTask },
    );
    expect(reconciled.activeAnswerTask?.id).toBe("answer-new");
    expect(reconciled.questions[0]?.id).toBe(currentQuestion.id);
    expect(reconciled.questions.map(question => question.id)).toContain(oldQuestion.id);
  });

  it("replaces a generating placeholder with a completed answer even when the answer is shorter", () => {
    const question = syntheticState.questions[0]!;
    const pendingQuestion = { ...question, status: "generating" as const, advice: { ...question.advice, detail: "正在调用当前对话模型生成回答，请稍候……" } };
    const completedQuestion = { ...question, status: "confirmed" as const, advice: { ...question.advice, detail: "最终答案。" } };
    const pendingTask = { id: "answer-same", interviewId: "demo", userId: "synthetic-user", billingUsageId: "usage", questionId: question.id, question: question.text, revision: 1, status: "generating" as const, updatedAtMs: 100 };
    const completedTask = { ...pendingTask, revision: 2, status: "completed" as const, completedText: "最终答案。", updatedAtMs: 200 };

    const reconciled = reconcileAnswerWorkspace(
      { questions: [pendingQuestion], activeAnswerTask: pendingTask },
      { questions: [completedQuestion], activeAnswerTask: completedTask },
    );

    expect(reconciled.questions[0]?.advice.detail).toBe("最终答案。");
    expect(reconciled.questions[0]?.status).toBe("confirmed");
  });

  it("keeps the longer streamed answer when an older same-task workspace snapshot arrives", () => {
    const question = syntheticState.questions[0]!;
    const streamedQuestion = {
      ...question,
      status: "streaming" as const,
      advice: { ...question.advice, detail: "这是已经展示的较长合成回答，后续内容仍在生成。" },
    };
    const staleQuestion = {
      ...question,
      status: "streaming" as const,
      advice: { ...question.advice, detail: "较短回答" },
    };
    const streamedTask = {
      id: "answer-same", interviewId: "demo", userId: "synthetic-user", billingUsageId: "usage",
      questionId: question.id, question: question.text, revision: 1, status: "generating" as const,
      partialText: streamedQuestion.advice.detail, updatedAtMs: 300,
    };
    const staleTask = { ...streamedTask, partialText: staleQuestion.advice.detail, updatedAtMs: 200 };

    const reconciled = reconcileAnswerWorkspace(
      { questions: [streamedQuestion], activeAnswerTask: streamedTask },
      { questions: [staleQuestion], activeAnswerTask: staleTask },
    );

    expect(reconciled.activeAnswerTask?.partialText).toBe(streamedQuestion.advice.detail);
    expect(reconciled.questions[0]?.advice.detail).toBe(streamedQuestion.advice.detail);
  });

  it("lets an explicit server task replace its local placeholder despite client clock skew", () => {
    const localQuestion = syntheticState.questions[0]!;
    const serverQuestion = { ...localQuestion, id: "server-question", text: "显式提交后的合成问题" };
    const localTask = { id: "pending:local", interviewId: "demo", userId: "synthetic-user", billingUsageId: "pending:local", questionId: localQuestion.id, question: localQuestion.text, revision: 1, status: "generating" as const, updatedAtMs: 9_999 };
    const serverTask = { ...localTask, id: "answer-server", billingUsageId: "live-answer:server", questionId: serverQuestion.id, question: serverQuestion.text, updatedAtMs: 100 };

    const reconciled = reconcileAnswerWorkspace(
      { questions: [localQuestion], activeAnswerTask: localTask },
      { questions: [serverQuestion], activeAnswerTask: serverTask },
      { preferIncomingTask: true },
    );

    expect(reconciled.activeAnswerTask?.id).toBe("answer-server");
    expect(reconciled.questions[0]?.id).toBe("server-question");
  });
});
