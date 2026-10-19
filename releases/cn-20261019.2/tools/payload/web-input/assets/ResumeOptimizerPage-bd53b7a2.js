import { n as e, t } from "./jsx-runtime-2Zwg-L3c.js";
import { A as n, F as r, I as i, a, k as o } from "./main-8b805158.js";
import { n as s, t as c } from "./src-D3iT3zfr.js";
import { a as l, t as u } from "./auth-client-CpBLJDBI.js";
var { useEffect: d, useRef: f, useState: p } = e();
//#endregion
//#region artifacts/cn-resume-optimizer-safe-edits-20261018/web/module-src/router.ts
function ee() {
	return [new URLSearchParams(i().search)];
}
//#endregion
//#region artifacts/cn-resume-optimizer-safe-edits-20261018/web/module-src/library-processing-polling.ts
var m = /* @__PURE__ */ new Set([
	"ready",
	"failed",
	"deleted",
	"disabled"
]), h = (e, t) => new Promise((n, r) => {
	let i = window.setTimeout(() => {
		t.removeEventListener("abort", a), n();
	}, e), a = () => {
		window.clearTimeout(i), t.removeEventListener("abort", a), r(new DOMException("The operation was aborted", "AbortError"));
	};
	if (t.aborted) {
		a();
		return;
	}
	t.addEventListener("abort", a, { once: !0 });
});
async function te({ documentId: e, loadState: t, signal: n, maxAttempts: r = 45, sleep: i = h }) {
	for (let a = 0; a < r; a += 1) {
		await i(a === 0 ? 800 : 2e3, n);
		let r = await t(n), o = r.librarySources.find((t) => t.id === e), s = r.knowledgeDocuments.find((t) => t.id === e), c = (o == null ? void 0 : o.status) ?? (s == null ? void 0 : s.status);
		if (c && m.has(c)) return {
			kind: "settled",
			state: r
		};
	}
	return { kind: "timeout" };
}
//#endregion
//#region artifacts/cn-resume-optimizer-safe-edits-20261018/web/module-src/runtime-config.ts
function g() {
	return { apiBaseUrl: "/" };
}
//#endregion
//#region \0@oxc-project+runtime@0.137.0/helpers/esm/typeof.js
function _(e) {
	"@babel/helpers - typeof";
	return _ = typeof Symbol == "function" && typeof Symbol.iterator == "symbol" ? function(e) {
		return typeof e;
	} : function(e) {
		return e && typeof Symbol == "function" && e.constructor === Symbol && e !== Symbol.prototype ? "symbol" : typeof e;
	}, _(e);
}
//#endregion
//#region \0@oxc-project+runtime@0.137.0/helpers/esm/toPrimitive.js
function ne(e, t) {
	if (_(e) != "object" || !e) return e;
	var n = e[Symbol.toPrimitive];
	if (n !== void 0) {
		var r = n.call(e, t || "default");
		if (_(r) != "object") return r;
		throw TypeError("@@toPrimitive must return a primitive value.");
	}
	return (t === "string" ? String : Number)(e);
}
//#endregion
//#region \0@oxc-project+runtime@0.137.0/helpers/esm/toPropertyKey.js
function re(e) {
	var t = ne(e, "string");
	return _(t) == "symbol" ? t : t + "";
}
//#endregion
//#region \0@oxc-project+runtime@0.137.0/helpers/esm/defineProperty.js
function v(e, t, n) {
	return (t = re(t)) in e ? Object.defineProperty(e, t, {
		value: n,
		enumerable: !0,
		configurable: !0,
		writable: !0
	}) : e[t] = n, e;
}
//#endregion
//#region artifacts/cn-resume-optimizer-safe-edits-20261018/web/module-src/resume-optimizer-client.ts
var y = {
	resume_optimizer_insufficient_balance: "可用积分不足 100，请充值或开通时间会员后刷新报价。",
	resume_optimizer_points_confirmation_required: "请明确确认本次 100 积分费用后再开始。",
	resume_optimizer_disabled: "简历优化暂时不可用，请稍后重试。",
	resume_optimizer_membership_required: "请刷新本次优化报价后重试。",
	resume_optimizer_daily_limit: "今日免费次数已用完，请刷新报价后确认是否使用积分。",
	resume_optimizer_busy: "简历优化正在忙碌，请稍后重试。",
	resume_optimizer_not_found: "这次优化已不可用，源资料可能已删除。",
	resume_optimizer_source_unavailable: "所选资料已变化或尚未解析完成，请刷新资料并选择当前版本。",
	resume_optimizer_source_markup_unsupported: "简历或岗位描述含不支持的格式，请上传不含 HTML 标记的纯文本或 Markdown 版本后重试。本次未扣费或占用免费次数。",
	resume_optimizer_idempotency_conflict: "提交内容已变化，请核对输入后重新提交。",
	resume_optimizer_revision_conflict: "其他页面已保存更新版本。已保留你的本地编辑，请重新载入已保存稿后继续。",
	resume_optimizer_not_completed: "请等待优化完成后再编辑或下载。",
	resume_optimizer_invalid_draft: "请填写字数范围内的纯文本或 Markdown，不支持 HTML 和脚本。",
	resume_optimizer_provider_unconfigured: "简历优化暂时不可用，请稍后重试。",
	resume_optimizer_export_unavailable: "暂时无法生成此格式。可尝试 Word，或移除不支持的字符后重试。已保存稿不受影响。",
	resume_optimizer_quote_changed: "本次报价已变化，请核对最新免费次数和积分费用后重新确认。"
}, b = "本次积分或免费次数已退还。", x = "未生成可用优化稿，原简历保留。", S = {
	invalid_output: [
		"AI 返回的结果超过处理上限，未能生成优化稿。原简历无需重新上传，请稍后重试。",
		"AI 返回的结果格式不完整，未能生成优化稿。原简历无需重新上传，请稍后重试。",
		"AI 返回的结果被截断，未能生成完整优化稿。原简历无需重新上传，请稍后重试。",
		"AI 未正常完成生成，本次没有可用优化稿。原简历无需重新上传，请稍后重试。",
		"AI 返回的结果存在重复字段，未能可靠读取。原简历无需重新上传，请稍后重试。",
		"AI 返回的评分维度不完整，未能生成可靠评估。原简历无需重新上传，请稍后重试。",
		"AI 返回的依据与原简历或岗位描述不一致，已停止生成。原简历无需重新上传，请稍后重试。",
		"AI 未按要求提供中文说明，未能生成可用结果。原简历无需重新上传，请稍后重试。",
		"AI 返回的待补充说明不符合要求，未能生成可用结果。原简历无需重新上传，请稍后重试。",
		"AI 返回的改写位置无法与原简历唯一对应，已停止生成。原简历无需重新上传，请稍后重试。",
		"AI 改写未通过原文事实检查，已停止生成。原简历无需重新上传，请稍后重试。",
		"AI 返回的修改位置相互重叠，未能安全合并优化稿。原简历无需重新上传，请稍后重试。",
		"AI 优化稿未通过完整性检查，未能安全交付。原简历无需重新上传，请稍后重试。",
		"本次未生成可安全应用的有效修改，原简历已保留。"
	],
	provider_timeout: ["AI 服务响应超时，请稍后重试，原简历无需重新上传。", "简历优化处理超时，请稍后重试，原简历无需重新上传。"],
	provider_unavailable: ["AI 服务暂时不可用，请稍后重试，原简历无需重新上传。"],
	provider_unconfigured: ["简历优化的 AI 服务尚未就绪，请联系支持人员检查服务配置。"],
	interrupted: [
		"简历优化处理已中断，请稍后重新发起，原简历无需重新上传。",
		"简历优化处理遇到内部错误，请稍后重试；若仍失败请联系支持人员。",
		"简历优化状态暂时无法处理，请稍后重试；若仍失败请联系支持人员。"
	]
};
function ie(e) {
	if (typeof e.errorCode != "string") return x;
	let t = e.errorCode ?? "", n = Object.prototype.hasOwnProperty.call(y, t) ? y[t] : x;
	return e.status !== "failed" || ![
		"reserved",
		"settled",
		"released"
	].includes(e.allowanceStatus) || !Object.prototype.hasOwnProperty.call(S, t) ? n : S[t].find((t) => e.errorMessage === t || e.allowanceStatus === "released" && e.errorMessage === t + b) ?? n;
}
var ae = (e, t) => typeof e == "object" && !!e && !Array.isArray(e) && Object.keys(e).length === t.length && t.every((t) => Object.prototype.hasOwnProperty.call(e, t)), C = (e) => typeof e == "number" && Number.isInteger(e) && e >= 0 && e <= 24;
function oe(e) {
	var t;
	if (e.status !== "completed") return null;
	let n = (t = e.review) == null ? void 0 : t.editSummary;
	if (!ae(n, [
		"proposedCount",
		"appliedCount",
		"retainedCount",
		"retainedReasonCounts"
	])) return null;
	let { proposedCount: r, appliedCount: i, retainedCount: a, retainedReasonCounts: o } = n;
	if (!C(r) || !C(i) || !C(a) || i < 1 || r !== i + a || !ae(o, [
		"factCheck",
		"sourceQuote",
		"overlap",
		"unchanged"
	])) return null;
	let s = Object.values(o);
	return !s.every(C) || s.reduce((e, t) => e + t, 0) !== a ? null : a ? `AI 初稿：已采用 ${i} 项改写，${a} 项改写未采用，请核实。` : `AI 初稿：已采用 ${i} 项改写。`;
}
var w = class extends Error {
	constructor(e, t) {
		super(y[e] ?? (t === 401 ? "登录已过期，请重新登录。" : t >= 500 ? "简历优化暂时不可用，请稍后重试。" : "操作未完成，请刷新后重试。")), v(this, "code", void 0), v(this, "status", void 0), this.code = e, this.status = t, this.name = "ResumeOptimizerError";
	}
}, T = new class {
	constructor(e, t = (e, t) => globalThis.fetch(e, t)) {
		v(this, "baseUrl", void 0), v(this, "fetchImpl", void 0), this.baseUrl = e, this.fetchImpl = t;
	}
	async response(e, t = {}, n) {
		let r = u.readStoredSession(), i = new Headers(t.headers);
		r && i.set("Authorization", `Bearer ${r.accessToken}`), typeof t.body == "string" && i.set("Content-Type", "application/json"), i.set("Accept", e.includes("/export?") ? "application/octet-stream" : "application/json");
		let a;
		try {
			a = await this.fetchImpl(l(this.baseUrl, `/api/v1/resume-optimizer${e}`), {
				...t,
				headers: i,
				cache: "no-store",
				...n ? { signal: n } : {}
			});
		} catch (e) {
			throw n != null && n.aborted || e instanceof DOMException && e.name === "AbortError" ? e : Error("无法连接简历优化服务，请检查网络后重试。");
		}
		if (!a.ok) {
			let e = "";
			try {
				var o, s;
				let t = await a.json();
				e = (t == null || (o = t.error) == null || (o = o.details) == null ? void 0 : o.errorCode) ?? (t == null || (s = t.error) == null ? void 0 : s.code) ?? "";
			} catch {}
			throw new w(e, a.status);
		}
		return a;
	}
	async json(e, t = {}, n) {
		var r;
		let i = await (await this.response(e, t, n)).json();
		if (i.success === !1 || i.data == null) throw new w((i == null || (r = i.error) == null || (r = r.details) == null ? void 0 : r.errorCode) ?? "", 500);
		return i.data;
	}
	capabilities(e) {
		return this.json("/capabilities", {}, e);
	}
	list(e) {
		return this.json("/jobs", {}, e);
	}
	get(e, t) {
		return this.json(`/jobs/${encodeURIComponent(e)}`, {}, t);
	}
	create(e, t) {
		return this.json("/jobs", {
			method: "POST",
			body: JSON.stringify(e)
		}, t);
	}
	cancel(e, t) {
		return this.json(`/jobs/${encodeURIComponent(e)}/cancel`, { method: "POST" }, t);
	}
	remove(e, t) {
		return this.json(`/jobs/${encodeURIComponent(e)}`, { method: "DELETE" }, t);
	}
	saveDraft(e, t, n, r) {
		return this.json(`/jobs/${encodeURIComponent(e)}/draft`, {
			method: "PATCH",
			body: JSON.stringify({
				expectedRevision: t,
				markdown: n
			})
		}, r);
	}
	saveAs(e, t, n) {
		return this.json(`/jobs/${encodeURIComponent(e)}/save-as`, {
			method: "POST",
			body: JSON.stringify({
				expectedRevision: t,
				confirmIndependentCopy: !0,
				factsConfirmed: !0
			})
		}, n);
	}
	async download(e, t, n, r) {
		var i, a;
		let o = await this.response(`/jobs/${encodeURIComponent(e)}/export?${new URLSearchParams({
			format: t,
			expectedRevision: String(n),
			factsConfirmed: "true"
		})}`, {}, r), s = t === "pdf" ? "application/pdf" : "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
		if (((i = o.headers.get("Content-Type")) == null || (i = i.split(";")[0]) == null ? void 0 : i.trim().toLowerCase()) !== s) throw Error("未收到有效的简历文件，请重试下载。");
		let c = await o.blob(), l = new Uint8Array(await c.slice(0, 5).arrayBuffer());
		if (!(t === "pdf" ? new TextDecoder().decode(l) === "%PDF-" : l[0] === 80 && l[1] === 75 && l[2] === 3 && l[3] === 4)) throw Error("未收到有效的简历文件，请重试下载。");
		let u = (a = o.headers.get("Content-Disposition")) == null || (a = a.match(/filename\*=UTF-8''([^;]+)/i)) == null ? void 0 : a[1], d = `优化后的简历.${t}`;
		if (u) try {
			d = decodeURIComponent(u);
		} catch {}
		return d = d.replace(/[\u0000-\u001f\u007f\u202a-\u202e\u2066-\u2069\\/]/g, "-").slice(0, 180), d.toLowerCase().endsWith(`.${t}`) || (d = `优化后的简历.${t}`), {
			blob: c,
			filename: d
		};
	}
}(g({
	BASE_URL: "/",
	DEV: !1,
	MODE: "production",
	PROD: !0,
	SSR: !1
}).apiBaseUrl);
function se({ blob: e, filename: t }) {
	let n = URL.createObjectURL(e), r = document.createElement("a");
	try {
		r.href = n, r.download = t, r.style.display = "none", document.body.appendChild(r), r.click();
	} finally {
		r.remove(), window.setTimeout(() => URL.revokeObjectURL(n), 1e3);
	}
}
//#endregion
//#region artifacts/cn-resume-optimizer-safe-edits-20261018/web/module-src/jsx-runtime.ts
var { jsx: E, jsxs: D, Fragment: ce } = t(), le = (e) => !!(e && (e.status === "queued" || e.status === "running")), O = (e) => e.status === "ready" && e.syncStatus !== "missing_artifacts" && e.selectable !== !1 && !!e.documentVersionId, ue = {
	completeness: "信息完整度",
	impact: "经历与成果依据",
	clarity: "表达清晰度",
	structure: "结构与可读性",
	roleMatch: "岗位匹配度"
}, de = {
	ready: "已就绪",
	processing: "解析中",
	processing_requested: "待解析",
	uploaded: "待解析",
	failed: "解析失败",
	disabled: "已停用"
}, fe = {
	queued: "排队中",
	running: "正在优化",
	completed: "已完成",
	failed: "优化失败",
	cancelled: "已取消"
}, pe = (e) => e instanceof Error ? e.message : "操作未完成，请稍后重试。", me = (e) => new Intl.DateTimeFormat("zh-CN", {
	dateStyle: "medium",
	timeStyle: "short",
	timeZone: "Asia/Shanghai"
}).format(e), he = 120;
function ge({ items: e }) {
	return /* @__PURE__ */ E("div", {
		className: "resume-evidence",
		children: e.map((e, t) => /* @__PURE__ */ D("blockquote", { children: [/* @__PURE__ */ E("small", { children: e.source === "jd" ? "解析后的岗位描述" : "解析后的简历" }), /* @__PURE__ */ E("p", { children: e.quote })] }, t))
	});
}
function _e({ state: e, setState: t }) {
	let [i] = ee(), [l, u] = p(null), [m, h] = p([]), [g, _] = p(null), [ne, re] = p(i.get("source") ?? ""), [v, y] = p(""), [b, x] = p("none"), [S, ae] = p(""), [C, he] = p(""), [_e, k] = p(!1), [A, j] = p(null), [M, N] = p("create"), [P, F] = p(!1), [ve, ye] = p(!1), [I, L] = p(""), [R, be] = p(!1), [xe, Se] = p(!0), [z, Ce] = p(""), [we, B] = p(""), [Te, V] = p(""), [Ee, De] = p(!1), H = f(null), Oe = f(!1), U = f(0), ke = f(/* @__PURE__ */ new Set()), Ae = f(0), W = f(null), je = f(null), Me = f(null), Ne = f(null), Pe = f(null), Fe = f(!1), Ie = e.librarySources.filter((t) => t.ownerUserId === e.account.id && t.kind === "resume" && t.status !== "deleted"), Le = e.librarySources.filter((t) => t.ownerUserId === e.account.id && t.kind === "jd" && t.status !== "deleted"), G = Ie.find((e) => e.id === ne || e.documentId === ne), K = Le.find((e) => e.id === S), q = (g == null ? void 0 : g.status) === "completed" && I !== g.draftMarkdown, Re = g ? oe(g) : null, J = le(g) || !!(l != null && l.activeJobId), ze = (l == null ? void 0 : l.billingClass) === "points", Be = f(null), Ve = (e) => {
		let t = JSON.stringify([
			e.quotaDay,
			e.billingClass,
			e.entryPoints
		]);
		Be.current !== t && (k(!1), j(null)), Be.current = t, u(e);
	};
	d(() => {
		var e;
		if (!A || !Me.current) return;
		let t = Me.current;
		return typeof t.showModal == "function" ? t.showModal() : t.setAttribute("open", ""), (e = Ne.current) == null || e.focus(), () => {
			t.open && typeof t.close == "function" && t.close(), Fe.current = !0;
		};
	}, [A]), d(() => {
		if (A || z || !Fe.current) return;
		Fe.current = !1;
		let e = Pe.current;
		e && !e.disabled && !e.closest("[hidden]") && e.focus();
	}, [A, z]);
	let Y = () => {
		var e;
		return (e = H.current) == null ? void 0 : e.signal;
	}, X = () => !!(H.current && !H.current.signal.aborted), Z = (e, t = !0) => {
		_(e), De(!1), h((t) => [e, ...t.filter((t) => t.jobId !== e.jobId)].slice(0, 30)), t && (L(e.draftMarkdown ?? ""), be(!1), F(!1), ye(!1));
	}, Q = async () => {
		let e = Y(), [t, n] = await Promise.all([T.capabilities(e), T.list(e)]);
		if (!(e != null && e.aborted || !X())) return Ve(t), h(n.jobs), t;
	}, He = async (e) => {
		let t = ++U.current, n = await T.get(e, Y());
		X() && t === U.current && Z(n);
	}, Ue = async () => {
		Se(!0), V("");
		try {
			let e = await T.capabilities(Y());
			if (!X()) return;
			if (Ve(e), e.enabled) {
				let t = await T.list(Y());
				if (!X()) return;
				h(t.jobs), e.activeJobId && (await He(e.activeJobId), X() && N("history"));
			}
		} catch (e) {
			X() && V(pe(e));
		} finally {
			X() && Se(!1);
		}
	};
	d(() => {
		let e = new AbortController();
		return H.current = e, Ue(), () => {
			e.abort(), U.current += 1, H.current = null;
		};
	}, []), d(() => {
		if (!g || g.billingClass !== "points") return;
		let r = `${g.jobId}:${g.billingStatus === "released" ? "refunded" : "charged"}`;
		if (ke.current.has(r)) return;
		ke.current.add(r);
		let i = ++Ae.current, a = Y();
		n.getBillingState(a).then((n) => {
			!X() || a != null && a.aborted || i !== Ae.current || t((t) => t.account.id === e.account.id ? {
				...t,
				billing: n
			} : t);
		}).catch(() => {
			ke.current.delete(r), X() && i === Ae.current && B("优化状态已更新，积分明细暂未同步；本页可用积分以最新报价为准，可到积分与会员页刷新。");
		});
	}, [
		g == null ? void 0 : g.jobId,
		g == null ? void 0 : g.billingClass,
		g == null ? void 0 : g.billingStatus
	]), d(() => {
		k(!1), j(null);
	}, [
		G == null ? void 0 : G.documentVersionId,
		K == null ? void 0 : K.documentVersionId,
		v,
		b,
		C
	]), d(() => {
		var e;
		if (!g || !le(g) || Ee) return;
		let t = new AbortController(), n = () => t.abort();
		(e = H.current) == null || e.signal.addEventListener("abort", n, { once: !0 });
		let r = U.current, i, a = 0, o = async () => {
			try {
				let e = await T.get(g.jobId, t.signal);
				if (t.signal.aborted || r !== U.current) return;
				if (_(e), h((t) => t.map((t) => t.jobId === e.jobId ? e : t)), !le(e)) {
					Z(e), await Q();
					return;
				}
				if (a += 1, a >= 120) {
					De(!0), B("任务仍在处理中，已暂停自动查询。可点击“刷新进度”查看最新结果。");
					return;
				}
				i = window.setTimeout(() => void o(), 2e3);
			} catch (e) {
				if (t.signal.aborted || r !== U.current) return;
				De(!0), V(pe(e)), e instanceof w && e.status === 404 && (_(null), L(""), F(!1), Q().catch(() => void 0));
			}
		};
		return i = window.setTimeout(() => void o(), 2e3), () => {
			var e;
			t.abort(), i !== void 0 && window.clearTimeout(i), (e = H.current) == null || e.signal.removeEventListener("abort", n);
		};
	}, [
		g == null ? void 0 : g.jobId,
		g == null ? void 0 : g.status,
		Ee
	]), d(() => {
		if (!(l != null && l.enabled)) return;
		let e = Math.max(100, Math.min(l.resetAtMs - l.nowMs + 100, 2147e6)), t = () => {
			Q().catch((e) => {
				X() && V(pe(e));
			});
		}, n = () => {
			document.visibilityState === "visible" && t();
		}, r = window.setTimeout(t, e);
		return window.addEventListener("focus", t), document.addEventListener("visibilitychange", n), () => {
			window.clearTimeout(r), window.removeEventListener("focus", t), document.removeEventListener("visibilitychange", n);
		};
	}, [
		l == null ? void 0 : l.resetAtMs,
		l == null ? void 0 : l.nowMs,
		l == null ? void 0 : l.enabled
	]);
	let $ = async (e, t) => {
		if (!Oe.current) {
			Oe.current = !0, Ce(e), V(""), B("");
			try {
				await t();
			} catch (e) {
				X() && V(pe(e));
			} finally {
				Oe.current = !1, X() && Ce("");
			}
		}
	}, We = async (e = Y()) => {
		let r = await n.loadState(e);
		return X() && !(e != null && e.aborted) && t(r), r;
	}, Ge = (t) => void $("upload", async () => {
		if (!c(t.name)) throw Error("请选择 PDF、DOCX、DOC、TXT 或 Markdown 简历。");
		if (t.size > 20 * 1024 * 1024) throw Error("请选择不超过 20 MB 的简历。");
		let n = await a.uploadResume(e.account.id, t, Y());
		if (!X() || (await We(), !X())) return;
		re(n.source.sourceId), k(!1), B("简历已上传，正在解析，完成后即可优化。");
		let r = await te({
			documentId: n.source.sourceId,
			signal: Y(),
			loadState: We
		});
		X() && B(r.kind === "timeout" ? "资料仍在解析中，稍后刷新资料即可查看状态。" : "资料处理已结束，请选择解析完成的简历继续。");
	}), Ke = (e = !1) => void $("create", async () => {
		var t;
		let n = l ? JSON.stringify([
			l.quotaDay,
			l.billingClass,
			l.entryPoints
		]) : null;
		if (!(l != null && l.enabled) || !l.canStart || J || !G || !O(G) || !_e || ze && (!e || A !== n)) return;
		let r = {
			sourceDocumentId: G.documentId ?? G.id,
			sourceVersionId: G.documentVersionId,
			targetRole: v.trim(),
			jdDocumentId: b === "material" ? (K == null ? void 0 : K.documentId) ?? (K == null ? void 0 : K.id) ?? null : null,
			jdVersionId: b === "material" ? (K == null ? void 0 : K.documentVersionId) ?? null : null,
			jdText: b === "text" ? C.trim() : "",
			quotedQuotaDay: l.quotaDay,
			quotedBillingClass: l.billingClass,
			quotedPoints: l.entryPoints,
			confirmPointsCharge: ze && e,
			confirmProcessing: !0
		};
		if (b === "material" && (!K || !O(K))) throw Error("请选择已解析完成的岗位描述后继续。");
		let { quotedQuotaDay: i, quotedBillingClass: a, quotedPoints: o, confirmPointsCharge: s, confirmProcessing: c, ...u } = r, d = JSON.stringify(u);
		((t = W.current) == null ? void 0 : t.fingerprint) !== d && (W.current = {
			fingerprint: d,
			key: crypto.randomUUID()
		});
		try {
			let e = await T.create({
				...r,
				idempotencyKey: W.current.key
			}, Y());
			if (!X()) return;
			Z(e), N("history"), W.current = null, k(!1), j(null), await Q();
		} catch (e) {
			throw X() && j(null), X() && e instanceof w && ((e.code === "resume_optimizer_quote_changed" || e.code === "resume_optimizer_insufficient_balance") && (k(!1), j(null), W.current = null), await Q().catch(() => void 0)), e;
		}
	}), qe = () => {
		ze && l ? j(JSON.stringify([
			l.quotaDay,
			l.billingClass,
			l.entryPoints
		])) : Ke();
	}, Je = (e) => {
		q && !window.confirm("放弃尚未保存的本地修改，并打开这次优化？") || $("open", () => He(e));
	}, Ye = async (e) => {
		if (e instanceof w && e.code === "resume_optimizer_revision_conflict" && g) {
			let e = await T.get(g.jobId, Y());
			X() && (Z(e, !1), be(!0), F(!1));
		} else e instanceof w && e.status === 404 && X() && (_(null), L(""), F(!1));
		throw e;
	}, Xe = () => {
		g && $("draft", async () => {
			try {
				let e = await T.saveDraft(g.jobId, g.revision, I, Y());
				X() && (Z(e), B("草稿已保存，原简历和 AI 初稿保留。"));
			} catch (e) {
				await Ye(e);
			}
		});
	}, Ze = (e) => {
		!g || !P || q || R || $(e, async () => {
			try {
				let t = await T.download(g.jobId, e, g.revision, Y());
				X() && (se(t), B(`${e === "docx" ? "Word" : "PDF"}已开始下载，内容来自已保存稿。`));
			} catch (e) {
				await Ye(e);
			}
		});
	};
	return /* @__PURE__ */ D("main", {
		className: "app-page resume-optimizer-page",
		children: [
			/* @__PURE__ */ D("header", {
				className: "page-header",
				children: [/* @__PURE__ */ D("div", { children: [/* @__PURE__ */ E("h1", { children: "简历优化" }), /* @__PURE__ */ E("p", { children: "让你的经历，表达得更清楚。" })] }), /* @__PURE__ */ E(r, {
					className: "button ghost",
					to: o.library,
					children: "我的资料"
				})]
			}),
			Te ? /* @__PURE__ */ E("div", {
				className: "inline-error",
				role: "alert",
				children: Te
			}) : null,
			we ? /* @__PURE__ */ E("div", {
				className: "billing-notice",
				role: "status",
				children: we
			}) : null,
			xe ? /* @__PURE__ */ E("section", {
				className: "panel resume-loading",
				role: "status",
				children: "正在加载…"
			}) : l ? l.enabled ? /* @__PURE__ */ D(ce, { children: [
				/* @__PURE__ */ D("div", {
					className: "resume-tabs",
					role: "tablist",
					"aria-label": "简历优化工作区",
					onKeyDown: (e) => {
						var t;
						if (![
							"ArrowLeft",
							"ArrowRight",
							"Home",
							"End"
						].includes(e.key)) return;
						e.preventDefault();
						let n = e.key === "Home" ? "create" : e.key === "End" || M === "create" ? "history" : "create";
						N(n), (t = e.currentTarget.querySelector(`#resume-${n}-tab`)) == null || t.focus();
					},
					children: [/* @__PURE__ */ E("button", {
						id: "resume-create-tab",
						role: "tab",
						tabIndex: M === "create" ? 0 : -1,
						"aria-selected": M === "create",
						"aria-controls": "resume-create-panel",
						onClick: () => N("create"),
						children: "新建优化"
					}), /* @__PURE__ */ D("button", {
						id: "resume-history-tab",
						role: "tab",
						tabIndex: M === "history" ? 0 : -1,
						"aria-selected": M === "history",
						"aria-controls": "resume-history-panel",
						onClick: () => N("history"),
						children: ["我的优化记录", m.length ? /* @__PURE__ */ E("span", {
							"aria-hidden": "true",
							children: m.length
						}) : null]
					})]
				}),
				/* @__PURE__ */ D("section", {
					id: "resume-create-panel",
					role: "tabpanel",
					"aria-labelledby": "resume-create-tab",
					hidden: M !== "create",
					className: "panel resume-create",
					children: [
						/* @__PURE__ */ D("div", {
							className: "resume-form-heading",
							children: [/* @__PURE__ */ E("h2", { children: "从一份简历开始" }), /* @__PURE__ */ E("p", { children: "获取评分、修改建议与可下载的优化稿。原文件会保留。" })]
						}),
						/* @__PURE__ */ D("div", {
							className: "resume-field",
							children: [
								/* @__PURE__ */ D("div", {
									className: "resume-field-heading",
									children: [/* @__PURE__ */ E("label", {
										htmlFor: "optimizer-resume",
										children: "选择简历"
									}), /* @__PURE__ */ E("button", {
										type: "button",
										className: "resume-text-button",
										disabled: !!z,
										onClick: () => void $("materials", async () => {
											await We(), X() && B("资料已刷新。");
										}),
										children: "刷新资料"
									})]
								}),
								/* @__PURE__ */ D("div", {
									className: "resume-input-row",
									children: [
										/* @__PURE__ */ D("select", {
											id: "optimizer-resume",
											value: (G == null ? void 0 : G.id) ?? ne,
											disabled: !!z || J,
											onChange: (e) => {
												re(e.target.value), k(!1), j(null);
											},
											children: [/* @__PURE__ */ E("option", {
												value: "",
												children: "请选择简历"
											}), Ie.map((e) => /* @__PURE__ */ D("option", {
												value: e.id,
												disabled: !O(e),
												children: [
													e.displayName,
													" · ",
													O(e) ? e.version : e.status === "ready" ? "请刷新版本" : de[e.status] ?? "暂不可用"
												]
											}, e.id))]
										}),
										/* @__PURE__ */ E("button", {
											className: "button ghost",
											disabled: !!z || J,
											onClick: () => {
												var e;
												return (e = je.current) == null ? void 0 : e.click();
											},
											children: z === "upload" ? "正在处理…" : "上传简历"
										}),
										/* @__PURE__ */ E("input", {
											ref: je,
											type: "file",
											accept: s,
											"aria-label": "上传简历文件",
											hidden: !0,
											onChange: (e) => {
												var t;
												let n = (t = e.target.files) == null ? void 0 : t[0];
												e.target.value = "", n && Ge(n);
											}
										})
									]
								}),
								Ie.length ? null : /* @__PURE__ */ E("p", {
									className: "resume-muted",
									children: "支持 PDF、Word、TXT 和 Markdown。"
								}),
								G && !O(G) ? /* @__PURE__ */ E("p", {
									className: "resume-muted",
									children: "这份简历尚未就绪，请解析完成后刷新资料。"
								}) : null
							]
						}),
						/* @__PURE__ */ D("div", {
							className: "resume-field",
							children: [/* @__PURE__ */ D("label", {
								htmlFor: "optimizer-role",
								children: ["目标岗位 ", /* @__PURE__ */ E("span", { children: "选填" })]
							}), /* @__PURE__ */ E("input", {
								id: "optimizer-role",
								value: v,
								maxLength: l.limits.targetRoleCharacters,
								placeholder: "例如：后端工程师",
								disabled: !!z || J,
								onChange: (e) => {
									y(e.target.value), k(!1);
								}
							})]
						}),
						/* @__PURE__ */ D("details", {
							className: "resume-jd",
							children: [/* @__PURE__ */ D("summary", { children: ["添加岗位描述 ", /* @__PURE__ */ E("span", { children: "可选，让建议更有针对性" })] }), /* @__PURE__ */ D("div", {
								className: "resume-jd-content",
								children: [
									/* @__PURE__ */ E("label", {
										className: "sr-only",
										htmlFor: "optimizer-jd-mode",
										children: "岗位描述"
									}),
									/* @__PURE__ */ D("select", {
										id: "optimizer-jd-mode",
										value: b,
										disabled: !!z || J,
										onChange: (e) => {
											x(e.target.value), k(!1);
										},
										children: [
											/* @__PURE__ */ E("option", {
												value: "none",
												children: "通用简历诊断，不提供 JD"
											}),
											/* @__PURE__ */ E("option", {
												value: "text",
												children: "粘贴岗位描述"
											}),
											/* @__PURE__ */ E("option", {
												value: "material",
												children: "选择资料库中的 JD"
											})
										]
									}),
									b === "text" ? /* @__PURE__ */ D(ce, { children: [
										/* @__PURE__ */ E("label", {
											className: "sr-only",
											htmlFor: "optimizer-jd-text",
											children: "岗位描述正文"
										}),
										/* @__PURE__ */ E("textarea", {
											id: "optimizer-jd-text",
											rows: 6,
											value: C,
											maxLength: l.limits.jdCharacters,
											disabled: !!z || J,
											onChange: (e) => {
												he(e.target.value), k(!1);
											},
											placeholder: "粘贴岗位职责和要求"
										}),
										/* @__PURE__ */ D("small", {
											className: "resume-muted",
											children: [
												C.length.toLocaleString(),
												" / ",
												l.limits.jdCharacters.toLocaleString(),
												" 字"
											]
										})
									] }) : b === "material" ? /* @__PURE__ */ D("select", {
										"aria-label": "资料库中的 JD",
										value: S,
										disabled: !!z || J,
										onChange: (e) => {
											ae(e.target.value), k(!1), j(null);
										},
										children: [/* @__PURE__ */ E("option", {
											value: "",
											children: "请选择已解析完成的岗位描述"
										}), Le.map((e) => /* @__PURE__ */ D("option", {
											value: e.id,
											disabled: !O(e),
											children: [
												e.displayName,
												" · ",
												O(e) ? e.version : de[e.status] ?? "暂不可用"
											]
										}, e.id))]
									}) : /* @__PURE__ */ E("p", {
										className: "resume-muted",
										children: "未提供 JD 时进行通用简历诊断，不评估岗位匹配度。"
									})
								]
							})]
						}),
						/* @__PURE__ */ D("div", {
							className: "resume-start-footer",
							children: [
								/* @__PURE__ */ D("label", {
									className: "resume-check",
									children: [/* @__PURE__ */ E("input", {
										type: "checkbox",
										checked: _e,
										disabled: !!z || J,
										onChange: (e) => k(e.target.checked)
									}), /* @__PURE__ */ E("span", { children: "我同意使用 AI 处理所选资料并保存优化结果。" })]
								}),
								/* @__PURE__ */ D("details", {
									className: "resume-disclosure",
									children: [
										/* @__PURE__ */ E("summary", { children: "处理与使用说明" }),
										/* @__PURE__ */ E("p", { children: "所选简历和岗位描述将发送至配置的 AI 服务。输入快照、建议和草稿随任务保存，直到你删除任务；删除引用的源资料也会清理对应优化内容。" }),
										/* @__PURE__ */ E("p", { children: "有效时间会员每日免费 3 次，与模拟面试次数独立。编辑、下载和另存不再收费。未完成任务失败或取消时，退还原创建日次数或原扣积分一次；已完成后删除不退还。" })
									]
								}),
								/* @__PURE__ */ E("button", {
									ref: Pe,
									className: "button primary full",
									disabled: !!z || J || !ze && !l.canStart || !G || !O(G) || !_e || b === "material" && (!K || !O(K)) || b === "text" && !C.trim(),
									onClick: qe,
									children: z === "create" ? "正在开始优化…" : J ? "已有优化任务处理中" : "开始优化"
								})
							]
						})
					]
				}),
				/* @__PURE__ */ D("section", {
					id: "resume-history-panel",
					role: "tabpanel",
					"aria-labelledby": "resume-history-tab",
					hidden: M !== "history",
					className: "resume-history",
					children: [/* @__PURE__ */ D("div", {
						className: "resume-history-heading",
						children: [/* @__PURE__ */ E("h2", { children: "优化记录" }), /* @__PURE__ */ E("button", {
							className: "resume-text-button",
							disabled: !!z,
							onClick: () => void $("refresh", async () => {
								await Q();
							}),
							children: "刷新"
						})]
					}), m.length ? /* @__PURE__ */ E("ul", { children: m.map((e) => /* @__PURE__ */ E("li", { children: /* @__PURE__ */ D("button", {
						className: (g == null ? void 0 : g.jobId) === e.jobId ? "selected" : "",
						disabled: !!z,
						onClick: () => Je(e.jobId),
						children: [/* @__PURE__ */ D("span", { children: [/* @__PURE__ */ E("strong", { children: e.sourceDisplayName }), /* @__PURE__ */ D("small", { children: [
							e.targetRole || "通用简历诊断",
							" · ",
							me(e.createdAtMs)
						] })] }), /* @__PURE__ */ E("span", {
							className: `resume-status ${e.status}`,
							children: fe[e.status]
						})]
					}) }, e.jobId)) }) : /* @__PURE__ */ D("div", {
						className: "resume-empty",
						children: [
							/* @__PURE__ */ E("h3", { children: "还没有优化记录" }),
							/* @__PURE__ */ E("p", { children: "完成第一次优化后，在这里查看。" }),
							/* @__PURE__ */ E("button", {
								className: "resume-text-button",
								onClick: () => N("create"),
								children: "选择一份简历开始"
							})
						]
					})]
				}),
				A ? /* @__PURE__ */ D("dialog", {
					ref: Me,
					className: "resume-payment-dialog",
					"aria-labelledby": "resume-payment-title",
					"aria-describedby": "resume-payment-description",
					onCancel: (e) => {
						e.preventDefault(), z || j(null);
					},
					children: [
						/* @__PURE__ */ E("h2", {
							id: "resume-payment-title",
							children: "确认本次优化"
						}),
						/* @__PURE__ */ D("p", {
							id: "resume-payment-description",
							children: [
								"本次开始优化将扣除 ",
								/* @__PURE__ */ E("strong", { children: "100 积分" }),
								"。"
							]
						}),
						/* @__PURE__ */ D("p", {
							className: "resume-payment-balance",
							children: ["可用积分 ", /* @__PURE__ */ E("strong", { children: l.availablePoints })]
						}),
						/* @__PURE__ */ E("p", {
							className: "resume-muted",
							children: "未完成任务失败或取消，积分将原路退还。编辑和下载不再收费。"
						}),
						l.availablePoints < 100 ? /* @__PURE__ */ D("div", {
							className: "resume-payment-insufficient",
							role: "status",
							children: [/* @__PURE__ */ E("p", { children: "积分不足 100，请充值或开通会员后重试。" }), /* @__PURE__ */ E(r, {
								to: o.billing,
								children: "充值 / 开通会员"
							})]
						}) : null,
						/* @__PURE__ */ D("div", {
							className: "resume-actions",
							children: [/* @__PURE__ */ E("button", {
								ref: Ne,
								className: "button ghost",
								disabled: !!z,
								onClick: () => j(null),
								children: "取消"
							}), /* @__PURE__ */ E("button", {
								className: "button primary",
								disabled: !!z || !l.canStart || l.availablePoints < 100,
								onClick: () => Ke(!0),
								children: z === "create" ? "正在开始…" : "确认并开始"
							})]
						})
					]
				}) : null,
				g ? /* @__PURE__ */ D("section", {
					className: "resume-result",
					"aria-label": "当前简历优化",
					children: [/* @__PURE__ */ D("header", {
						className: "resume-result-header",
						children: [/* @__PURE__ */ D("div", { children: [
							/* @__PURE__ */ E("span", {
								className: "kicker",
								children: fe[g.status]
							}),
							/* @__PURE__ */ E("h2", { children: g.sourceDisplayName }),
							/* @__PURE__ */ D("p", { children: [
								g.targetRole || "通用简历诊断",
								" · ",
								g.hasJd ? "已提供岗位描述" : "未提供 JD",
								" · 稿件版本 ",
								g.revision
							] }),
							/* @__PURE__ */ D("p", { children: [
								g.billingClass === "points" ? `本次 ${g.pointsCharged} 积分` : "本次会员免费",
								" · ",
								g.billingStatus === "reserved" ? g.billingClass === "points" ? "已扣积分，等待结果" : "免费次数已占用" : g.billingStatus === "released" ? "已原路退还" : "已完成结算"
							] })
						] }), /* @__PURE__ */ E("button", {
							className: "button danger",
							disabled: !!z,
							onClick: () => {
								!g || !window.confirm("删除本次优化及其输入快照、建议和草稿？已经另存的新简历将保留。已完成的优化不会退还积分或恢复免费次数。") || $("delete", async () => {
									U.current += 1, await T.remove(g.jobId, Y()), X() && (U.current += 1, _(null), L(""), F(!1), await Q(), X() && B("本次优化及草稿已删除，已另存的新简历仍保留在资料库。"));
								});
							},
							children: z === "delete" ? "正在删除…" : "删除优化"
						})]
					}), le(g) ? /* @__PURE__ */ D("div", {
						className: "panel resume-progress",
						role: "status",
						children: [
							/* @__PURE__ */ E("div", {
								className: "resume-progress-dot",
								"aria-hidden": "true"
							}),
							/* @__PURE__ */ E("h3", { children: g.status === "queued" ? "优化任务正在排队" : "正在根据原文整理改进建议" }),
							/* @__PURE__ */ E("p", { children: g.status === "queued" ? "任务按顺序处理，你可以离开页面，稍后回来查看。" : "正在核对依据、诊断简历并生成优化稿，请稍候。" }),
							/* @__PURE__ */ D("div", {
								className: "resume-actions",
								children: [/* @__PURE__ */ E("button", {
									className: "button ghost",
									disabled: !!z,
									onClick: () => void $("status", () => He(g.jobId)),
									children: "刷新进度"
								}), /* @__PURE__ */ E("button", {
									className: "button danger",
									disabled: !!z,
									onClick: () => void $("cancel", async () => {
										U.current += 1;
										let e = await T.cancel(g.jobId, Y());
										X() && (Z(e), await Q());
									}),
									children: z === "cancel" ? "正在取消…" : "取消优化"
								})]
							})
						]
					}) : g.status === "failed" || g.status === "cancelled" ? /* @__PURE__ */ D("div", {
						className: "panel resume-empty",
						children: [
							/* @__PURE__ */ E("h3", { children: g.status === "cancelled" ? "本次优化已取消" : "本次优化未完成" }),
							/* @__PURE__ */ E("p", { children: g.status === "failed" ? ie(g) : "系统不会自动开始新的优化。" }),
							/* @__PURE__ */ E("p", { children: g.allowanceStatus === "released" ? g.billingClass === "points" ? "本次扣除的 100 积分已原路退还。" : "已退还原创建日的免费次数，跨日不会增加今日额度。" : "请刷新最新次数和费用后重新开始。" }),
							/* @__PURE__ */ E("button", {
								className: "button primary",
								disabled: !!z,
								onClick: () => {
									var e;
									g && (re(g.sourceDocumentId), y(g.targetRole), x(g.jdDocumentId ? "material" : g.jdText ? "text" : "none"), ae(((e = Le.find((e) => e.documentId === g.jdDocumentId || e.id === g.jdDocumentId)) == null ? void 0 : e.id) ?? ""), he(g.jdText), k(!1), j(null), W.current = null, _(null), N("create"), L(""), F(!1), B("请核对资料，重新确认后再开始。系统不会自动重试或收费。"));
								},
								children: "核对输入并重试"
							})
						]
					}) : g.review ? /* @__PURE__ */ D(ce, { children: [
						/* @__PURE__ */ D("div", {
							className: "resume-review-layout",
							children: [/* @__PURE__ */ D("section", {
								className: "panel resume-score",
								children: [
									/* @__PURE__ */ E("span", {
										className: "kicker",
										children: "参考评分"
									}),
									/* @__PURE__ */ D("div", {
										className: "resume-score-number",
										children: [/* @__PURE__ */ E("strong", { children: g.review.overallScore }), /* @__PURE__ */ E("span", { children: "/ 100" })]
									}),
									/* @__PURE__ */ E("p", { children: g.review.disclaimer }),
									/* @__PURE__ */ E("small", { children: "各维度等权计算" }),
									g.review.roleMatchingAssessed ? null : /* @__PURE__ */ E("p", {
										className: "resume-muted",
										children: "未提供岗位描述，岗位匹配度未评估。"
									})
								]
							}), /* @__PURE__ */ D("section", {
								className: "panel resume-dimensions",
								children: [/* @__PURE__ */ E("h3", { children: "评分维度与依据" }), g.review.dimensions.map((e) => /* @__PURE__ */ D("article", { children: [
									/* @__PURE__ */ D("div", { children: [/* @__PURE__ */ E("strong", { children: ue[e.key] ?? e.key }), /* @__PURE__ */ D("span", { children: [e.score, " / 100"] })] }),
									/* @__PURE__ */ E("meter", {
										min: 0,
										max: 100,
										value: e.score,
										"aria-label": `${ue[e.key] ?? e.key}评分`,
										children: e.score
									}),
									/* @__PURE__ */ E("p", { children: e.reason }),
									/* @__PURE__ */ E(ge, { items: e.evidence })
								] }, e.key))]
							})]
						}),
						/* @__PURE__ */ D("section", {
							className: "panel resume-suggestions",
							children: [
								/* @__PURE__ */ E("h3", { children: "修改建议" }),
								g.review.suggestions.map((e, t) => /* @__PURE__ */ D("article", { children: [
									/* @__PURE__ */ E("span", {
										className: `resume-priority ${e.priority}`,
										children: {
											high: "优先修改",
											medium: "建议修改",
											low: "可选完善"
										}[e.priority]
									}),
									/* @__PURE__ */ E("h4", { children: e.title }),
									/* @__PURE__ */ E("p", { children: e.explanation }),
									/* @__PURE__ */ E(ge, { items: e.evidence }),
									/* @__PURE__ */ D("p", {
										className: "resume-recommendation",
										children: [/* @__PURE__ */ E("strong", { children: "建议修改方式" }), e.recommendation]
									})
								] }, t)),
								g.review.missingFacts.length ? /* @__PURE__ */ D("aside", {
									className: "resume-missing",
									children: [
										/* @__PURE__ */ E("h4", { children: "需要你补充的信息" }),
										/* @__PURE__ */ E("p", { children: "仅补充真实且可核实的信息，这些内容未被虚构到优化稿中。" }),
										/* @__PURE__ */ E("ul", { children: g.review.missingFacts.map((e, t) => /* @__PURE__ */ E("li", { children: e }, t)) })
									]
								}) : null
							]
						}),
						/* @__PURE__ */ D("section", {
							className: "panel resume-comparison",
							children: [
								/* @__PURE__ */ E("div", {
									className: "panel-heading",
									children: /* @__PURE__ */ D("div", { children: [
										/* @__PURE__ */ E("h3", { children: "对照原文，编辑优化稿" }),
										/* @__PURE__ */ E("p", { children: "解析原文只读，原文件保留。修改后请先保存，再下载或另存新简历。" }),
										Re ? /* @__PURE__ */ E("p", {
											className: "resume-muted",
											"aria-label": "AI 初稿改写摘要",
											children: Re
										}) : null
									] })
								}),
								/* @__PURE__ */ D("div", {
									className: "resume-comparison-grid",
									children: [/* @__PURE__ */ D("section", { children: [
										/* @__PURE__ */ E("h4", { children: "解析后的原简历" }),
										/* @__PURE__ */ E("p", {
											className: "resume-muted",
											children: "展示解析文本，表格已转为简化文本。"
										}),
										/* @__PURE__ */ E("pre", { children: g.sourceText })
									] }), /* @__PURE__ */ D("section", { children: [
										/* @__PURE__ */ E("label", {
											htmlFor: "optimizer-draft",
											children: "可编辑优化稿"
										}),
										/* @__PURE__ */ E("textarea", {
											id: "optimizer-draft",
											rows: 22,
											value: I,
											maxLength: l.limits.draftCharacters,
											disabled: !!z,
											onChange: (e) => {
												L(e.target.value), F(!1), ye(!1);
											}
										}),
										/* @__PURE__ */ D("small", { children: [
											I.length.toLocaleString(),
											" / ",
											l.limits.draftCharacters.toLocaleString(),
											" 字 · ",
											q ? "尚未保存" : "已保存"
										] })
									] })]
								}),
								/* @__PURE__ */ D("details", { children: [/* @__PURE__ */ E("summary", { children: "查看 AI 初稿" }), /* @__PURE__ */ E("pre", { children: g.initialDraftMarkdown })] }),
								R ? /* @__PURE__ */ D("div", {
									className: "inline-error",
									role: "alert",
									children: ["服务端已有更新版本，已保留上方的本地编辑。请先复制需要保留的内容，再载入已保存稿。", /* @__PURE__ */ E("button", {
										className: "resume-text-button",
										onClick: () => {
											window.confirm("用最新已保存稿替换尚未保存的本地修改？") && (L(g.draftMarkdown ?? ""), be(!1), F(!1));
										},
										children: "载入已保存稿"
									})]
								}) : null,
								/* @__PURE__ */ D("div", {
									className: "resume-actions",
									children: [/* @__PURE__ */ E("button", {
										className: "button primary",
										disabled: !!z || !q || R || !I.trim(),
										onClick: Xe,
										children: z === "draft" ? "正在保存…" : "保存草稿"
									}), /* @__PURE__ */ E("span", {
										className: "resume-muted",
										children: "支持纯文本或 Markdown，不支持 HTML。"
									})]
								}),
								/* @__PURE__ */ D("div", {
									className: "resume-export-area",
									children: [
										/* @__PURE__ */ E("h4", { children: "下载或另存简历" }),
										/* @__PURE__ */ E("p", { children: "导出使用统一简洁模板，不保留原文件排版。使用前请核对每项经历、日期、技能和成果。" }),
										/* @__PURE__ */ D("label", {
											className: "resume-check",
											children: [/* @__PURE__ */ E("input", {
												type: "checkbox",
												checked: P,
												disabled: !!z || q || R,
												onChange: (e) => F(e.target.checked)
											}), /* @__PURE__ */ E("span", { children: "我已核对这份已保存稿，确认事实准确。" })]
										}),
										q ? /* @__PURE__ */ E("p", {
											className: "resume-muted",
											children: "请先保存修改，再确认事实并下载。"
										}) : null,
										/* @__PURE__ */ D("div", {
											className: "resume-actions",
											children: [l.exports.includes("docx") ? /* @__PURE__ */ E("button", {
												className: "button primary",
												disabled: !!z || q || R || !P,
												onClick: () => Ze("docx"),
												children: z === "docx" ? "正在生成 Word…" : "下载 Word"
											}) : null, l.exports.includes("pdf") ? /* @__PURE__ */ E("button", {
												className: "button ghost",
												disabled: !!z || q || R || !P,
												onClick: () => Ze("pdf"),
												children: z === "pdf" ? "正在生成 PDF…" : "下载 PDF"
											}) : null]
										}),
										/* @__PURE__ */ D("label", {
											className: "resume-check",
											children: [/* @__PURE__ */ E("input", {
												type: "checkbox",
												checked: ve,
												disabled: !!z || q || R,
												onChange: (e) => ye(e.target.checked)
											}), /* @__PURE__ */ E("span", { children: "在资料库另存一份独立新简历。原简历和既有面试选择保留，删除本次优化时新简历仍保留。" })]
										}),
										/* @__PURE__ */ E("button", {
											className: "button ghost",
											disabled: !!z || q || R || !P || !ve,
											onClick: () => {
												!g || !P || !ve || q || R || $("copy", async () => {
													try {
														if (await T.saveAs(g.jobId, g.revision, Y()), !X()) return;
														await He(g.jobId), await We(), X() && B("已在资料库另存一份新简历，解析完成后可用于面试。原简历和既有面试选择保留。");
													} catch (e) {
														await Ye(e);
													}
												});
											},
											children: z === "copy" ? "正在另存简历…" : g.savedDocumentId ? "刷新已另存状态" : "另存为新简历"
										}),
										g.savedDocumentId ? /* @__PURE__ */ D("p", {
											className: "resume-muted",
											children: ["此稿件版本已另存为新简历。 ", /* @__PURE__ */ E(r, {
												to: o.library,
												children: "打开资料库 →"
											})]
										}) : null,
										/* @__PURE__ */ E("p", {
											className: "resume-muted",
											children: "编辑、下载和另存不会再次收费或占用次数。任务及源资料保留时，会员到期后仍可使用已完成结果。"
										})
									]
								})
							]
						})
					] }) : /* @__PURE__ */ E("section", {
						className: "panel",
						role: "alert",
						children: "本次优化尚无可用结果，请刷新进度。"
					})]
				}) : null
			] }) : /* @__PURE__ */ D("section", {
				className: "panel resume-empty",
				children: [
					/* @__PURE__ */ E("h2", { children: "简历优化暂时不可用" }),
					/* @__PURE__ */ E("p", { children: "请稍后再试，也可继续使用面试和资料。" }),
					/* @__PURE__ */ E(r, {
						to: o.library,
						children: "管理资料 →"
					})
				]
			}) : /* @__PURE__ */ D("section", {
				className: "panel",
				children: [/* @__PURE__ */ E("p", { children: "暂时无法读取简历优化。" }), /* @__PURE__ */ E("button", {
					className: "button primary",
					onClick: () => void Ue(),
					children: "重试"
				})]
			})
		]
	});
}
//#endregion
export { he as RESUME_OPTIMIZER_POLL_LIMIT, _e as ResumeOptimizerPage };
