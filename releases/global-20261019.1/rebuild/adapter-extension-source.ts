export function installWrittenMultiScreen(adapter:any,deps:any){const{AppError,authHeaders,requireUserId,screenshotStageToTask,screenshotAnswerText,toSubmitScreenshotAnswerResult}=deps;class Extension{async getScreenshotCapturePolicy(signal?: AbortSignal) {
    const policy = await this.client.request<{ maxImagesPerTask: number; supportsCaptureOnly?: boolean }>(
      "/api/v1/screenshot-answer/validation-policy", { headers: authHeaders() }, signal,
    );
    if (policy.supportsCaptureOnly !== true || !Number.isInteger(policy.maxImagesPerTask) || policy.maxImagesPerTask < 1) {
      throw new AppError("validation", "Multi-screen answers are not supported by this service. Try again after the service is updated.");
    }
    return { maxImagesPerTask: Math.min(4, policy.maxImagesPerTask) };
  }
async captureScreenshot(command: { readonly interviewId: string }, signal?: AbortSignal, onStage?: (task: ScreenshotTask) => void): Promise<CollectedScreenshot> {
    const request = await this.createScreenshotRequest(command.interviewId, "remote-capture-requests", { captureOnly: true, instruction: "" }, signal);
    if (request.captureOnly !== true) {
      await this.cancelDesktopShortcutScreenshot(request.requestId).catch(() => undefined);
      throw new AppError("validation", "Capture-only mode is not supported by this service.");
    }
    const completed = await this.waitForScreenshotRequest(request, { ...command, instruction: "" }, signal, onStage);
    if (!completed.capturedImageId) throw new AppError("validation", "No valid image was returned. Capture again.");
    return { requestId: completed.requestId, imageId: completed.capturedImageId, name: completed.capturedFilename || "Shared screen capture" };
  }
async submitScreenshotBatch(command: { readonly interviewId: string; readonly captureRequestIds: readonly string[]; readonly instruction: string }, signal?: AbortSignal, onStage?: (task: ScreenshotTask) => void, onAnswerUpdate?: (result: SubmitManualAnswerResult) => void) {
    const request = await this.createScreenshotRequest(command.interviewId, "batch-answer-requests", {
      captureRequestIds: command.captureRequestIds, instruction: command.instruction,
    }, signal);
    const completed = await this.waitForScreenshotRequest(request, command, signal, onStage, onAnswerUpdate);
    if (!completed.answerTask) throw new AppError("validation", "No multi-screen answer was returned. Capture again and retry.");
    return toSubmitScreenshotAnswerResult(completed.answerTask, command.instruction);
  }
private createScreenshotRequest(interviewId: string, endpoint: "remote-capture-requests" | "batch-answer-requests", body: Record<string, unknown>, signal?: AbortSignal) {
    return this.client.request<BackendRemoteScreenshotCaptureRequestResponse>(`/api/v1/screenshot-answer/sessions/${encodeURIComponent(interviewId)}/${endpoint}`, {
      method: "POST", headers: authHeaders(), body: JSON.stringify({ userId: requireUserId(), ...body }),
    }, signal);
  }
private async waitForScreenshotRequest(
    initial: BackendRemoteScreenshotCaptureRequestResponse,
    command: { readonly interviewId: string; readonly instruction: string },
    signal?: AbortSignal,
    onStage?: (task: ScreenshotTask) => void,
    onAnswerUpdate?: (result: SubmitManualAnswerResult) => void,
  ): Promise<BackendRemoteScreenshotCaptureRequestResponse> {
    let firstRenderAcknowledgementScheduled = false;
    const acknowledgeFirstRender = (task: BackendScreenshotAnswerTaskResponse) => {
      const answerText = screenshotAnswerText(task);
      if (!answerText || firstRenderAcknowledgementScheduled) return;
      firstRenderAcknowledgementScheduled = true;
      const acknowledge = () => this.acknowledgeRuntimePerformance(
        command.interviewId, initial.requestId, "screenshot-first-render", initial.createdAtMs, task.taskId,
        { browserRenderAtMs: Date.now(), renderedTextLength: answerText.length, visibilityState: document.visibilityState },
      );
      if (typeof requestAnimationFrame === "function") requestAnimationFrame(acknowledge);
      else window.setTimeout(acknowledge, 0);
    };
    const consume = (current: BackendRemoteScreenshotCaptureRequestResponse) => {
      if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
      onStage?.(screenshotStageToTask(current));
      if (current.answerTask) {
        onAnswerUpdate?.(toSubmitScreenshotAnswerResult(current.answerTask, command.instruction));
        acknowledgeFirstRender(current.answerTask);
      }
      if (current.status === "cancelled") throw new DOMException("Aborted", "AbortError");
      if (current.status === "failed") throw new AppError("validation", `${current.stage ? `Capture stage ${current.stage} failed: ` : ""}${current.errorMessage || "Capture processing failed. Capture again and retry."}`);
      if (current.status !== "completed") return false;
      if (initial.captureOnly ? !current.capturedImageId : !current.answerTask) {
        throw new AppError("validation", "Capture processing returned an incomplete result. Capture again.");
      }
      return true;
    };
    try {
      if (consume(initial)) return initial;
      const deadlineAt = Date.now() + 120000;
      let recoveryDelayMs = 1000;
      while (Date.now() < deadlineAt) {
        if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
        const pushed = await this.waitForCaptureEvent(initial.requestId, recoveryDelayMs, signal);
        const current: BackendRemoteScreenshotCaptureRequestResponse = pushed
          ? { ...initial, ...pushed } as BackendRemoteScreenshotCaptureRequestResponse
          : await this.client.request<BackendRemoteScreenshotCaptureRequestResponse>(`/api/v1/screenshot-answer/capture-requests/${encodeURIComponent(initial.requestId)}?userId=${encodeURIComponent(requireUserId())}`, {
              method: "GET", headers: authHeaders(),
            }, signal);
        if (consume(current)) return current;
        recoveryDelayMs = pushed ? 1000 : Math.min(recoveryDelayMs * 2, 8000);
      }
      throw new AppError("network", initial.captureOnly
        ? "Capture timed out. Check that the Companion is connected and capture again."
        : "The screenshot answer timed out. Capture again and retry.");
    } catch (error) {
      await this.cancelDesktopShortcutScreenshot(initial.requestId).catch(() => undefined);
      throw error;
    } finally {
      this.pendingCaptureEvents.delete(initial.requestId);
    }
  }}for(const name of ["getScreenshotCapturePolicy","captureScreenshot","submitScreenshotBatch","createScreenshotRequest","waitForScreenshotRequest"])adapter[name]=Extension.prototype[name];}
