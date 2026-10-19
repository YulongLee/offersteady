import { A as e, C as t, F as n, L as r, R as i, k as a, t as o } from "./main-8b805158.js";
import { n as s, t as c } from "./jsx-runtime-2Zwg-L3c.js";
import { i as l } from "./auth-client-CpBLJDBI.js";
import { ConversationMonitor as u, ManualQuestionComposer as d, MobileInterviewControls as f, OriginalLivePage as p, WebSearchToggle as m, WorkspaceDivider as h } from "./LivePageLegacy-3f784701.js";
var { useEffect: g, useRef: _, useState: v, useMemo: y, useLayoutEffect: b } = s(), ee = (e, t) => e.filter((e) => e.ownerUserId === t && e.status !== "deleted"), te = (e) => e.status === "ready" && e.selectable !== !1, ne = (e, t) => {
	let n = new Set([
		t.resumeSourceId,
		t.jobDescriptionSourceId,
		...t.knowledgeSourceIds
	].filter(Boolean));
	return e.filter((e) => n.has(e.id));
}, x = [
	{
		id: "pdf",
		label: "PDF",
		extensions: [".pdf"],
		mimeTypes: ["application/pdf"]
	},
	{
		id: "docx",
		label: "DOCX",
		extensions: [".docx"],
		mimeTypes: ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
	},
	{
		id: "doc",
		label: "DOC",
		extensions: [".doc"],
		mimeTypes: [
			"application/msword",
			"application/doc",
			"application/vnd.ms-word"
		]
	},
	{
		id: "txt",
		label: "TXT",
		extensions: [".txt"],
		mimeTypes: ["text/plain"]
	},
	{
		id: "md",
		label: "MD",
		extensions: [".md"],
		mimeTypes: [
			"text/markdown",
			"text/x-markdown",
			"text/plain"
		]
	}
], re = {
	maxFileSizeBytes: 20 * 1024 * 1024,
	acceptedExtensions: x.flatMap((e) => e.extensions),
	acceptedMimeTypes: x.flatMap((e) => e.mimeTypes),
	label: x.map((e) => e.label).join("、")
};
re.acceptedExtensions.join(",");
//#endregion
//#region ../../../../../private/tmp/offersteady-cn-written-multi-screen/packages/protocol/src/speaker.ts
var S = (e) => e.terminalState ?? (e.isFinal ? "final" : null), ie = (e) => e === "final" ? 2 : +(e === "incomplete"), ae = (e, t) => {
	if (!e || e.id !== t.id) return !0;
	let n = S(e), r = S(t);
	return ie(r) < ie(n) || t.revision < e.revision ? !1 : t.revision > e.revision ? !0 : ie(r) > ie(n);
};
re.label, re.maxFileSizeBytes;
//#endregion
//#region ../../../../../private/tmp/offersteady-cn-written-multi-screen/packages/protocol/src/interview-language.ts
var oe = /* @__PURE__ */ new Set([
	"zh-CN",
	"en-US",
	"ja-JP",
	"ko-KR",
	"fr-FR",
	"de-DE",
	"es-ES",
	"pt-BR",
	"it-IT",
	"ru-RU"
]), C = {
	"zh-CN": [
		"Chinese",
		"中文",
		"zh",
		"Chinese"
	],
	"en-US": [
		"English",
		"English",
		"en",
		"English"
	],
	"ja-JP": [
		"Japanese",
		"日本語",
		"ja",
		"Japanese"
	],
	"ko-KR": [
		"Korean",
		"한국어",
		"ko",
		"Korean"
	],
	"vi-VN": [
		"Vietnamese",
		"Tiếng Việt",
		"vi",
		"Vietnamese"
	],
	"th-TH": [
		"Thai",
		"ไทย",
		"th",
		"Thai"
	],
	"id-ID": [
		"Indonesian",
		"Bahasa Indonesia",
		"id",
		"Indonesian"
	],
	"ms-MY": [
		"Malay",
		"Bahasa Melayu",
		"ms",
		"Malay"
	],
	"fil-PH": [
		"Filipino",
		"Filipino",
		"fil",
		"Filipino"
	],
	"hi-IN": [
		"Hindi",
		"हिन्दी",
		"hi",
		"Hindi"
	],
	"ar-SA": [
		"Arabic",
		"العربية",
		"ar",
		"Arabic"
	],
	"fr-FR": [
		"French",
		"Français",
		"fr",
		"French"
	],
	"de-DE": [
		"German",
		"Deutsch",
		"de",
		"German"
	],
	"es-ES": [
		"Spanish",
		"Español",
		"es",
		"Spanish"
	],
	"pt-BR": [
		"Portuguese",
		"Português",
		"pt",
		"Portuguese"
	],
	"ru-RU": [
		"Russian",
		"Русский",
		"ru",
		"Russian"
	],
	"it-IT": [
		"Italian",
		"Italiano",
		"it",
		"Italian"
	],
	"nl-NL": [
		"Dutch",
		"Nederlands",
		"nl",
		"Dutch"
	],
	"sv-SE": [
		"Swedish",
		"Svenska",
		"sv",
		"Swedish"
	],
	"da-DK": [
		"Danish",
		"Dansk",
		"da",
		"Danish"
	],
	"fi-FI": [
		"Finnish",
		"Suomi",
		"fi",
		"Finnish"
	],
	"nb-NO": [
		"Norwegian",
		"Norsk",
		"no",
		"Norwegian"
	],
	"el-GR": [
		"Greek",
		"Ελληνικά",
		"el",
		"Greek"
	],
	"pl-PL": [
		"Polish",
		"Polski",
		"pl",
		"Polish"
	],
	"cs-CZ": [
		"Czech",
		"Čeština",
		"cs",
		"Czech"
	],
	"hu-HU": [
		"Hungarian",
		"Magyar",
		"hu",
		"Hungarian"
	],
	"ro-RO": [
		"Romanian",
		"Română",
		"ro",
		"Romanian"
	],
	"bg-BG": [
		"Bulgarian",
		"Български",
		"bg",
		"Bulgarian"
	],
	"hr-HR": [
		"Croatian",
		"Hrvatski",
		"hr",
		"Croatian"
	],
	"sk-SK": [
		"Slovak",
		"Slovenčina",
		"sk",
		"Slovak"
	]
};
Object.keys(C).map((e) => {
	let [t, n, r, i] = C[e];
	return {
		locale: e,
		label: t,
		nativeLabel: n,
		asrLanguageCode: r,
		outputLanguage: i,
		tier: oe.has(e) ? "production" : "beta",
		direction: e === "ar-SA" ? "rtl" : "ltr"
	};
});
var w = 8, T = (e) => e.replace(/\s+/g, "").replace(/[，。！？、；：,.!?;:~～…·]/g, "").trim(), se = (e, t) => {
	let n = e.trim(), r = t.trim();
	if (!n) return r;
	if (!r) return n;
	let i = T(n), a = T(r);
	return i === a ? r.length >= n.length ? r : n : i.includes(a) ? n : a.includes(i) ? r : `${n} ${r}`;
}, ce = (e) => {
	let t = /* @__PURE__ */ new Map();
	for (let n of e) T(n.text) && ae(t.get(n.id), n) && t.set(n.id, n);
	return [...t.values()].sort((e, t) => e.startedAtMs - t.startedAtMs || e.revision - t.revision);
}, E = (e) => {
	let t = [], n = /* @__PURE__ */ new Map();
	for (let r of ce(e)) {
		if (r.isFinal) {
			t.push(r);
			continue;
		}
		let e = `${r.sourceKind}:${r.sourceId}`, i = n.get(e);
		(!i || r.endedAtMs > i.endedAtMs || r.endedAtMs === i.endedAtMs && r.revision > i.revision) && n.set(e, r);
	}
	return {
		confirmed: t,
		activeDrafts: [...n.values()]
	};
}, D = (e) => {
	let t = E(e);
	return [...t.confirmed, ...t.activeDrafts].sort((e, t) => e.startedAtMs - t.startedAtMs || e.revision - t.revision);
}, O = (e) => {
	let t = [];
	for (let n of D(e)) {
		let e = t.at(-1), r = e ? n.startedAtMs - e.endedAtMs : Infinity, i = (e == null ? void 0 : e.sourceSegmentIds) ?? [];
		if (!(e && e.sessionId === n.sessionId && e.role === n.role && e.sourceKind === n.sourceKind && e.isFinal === n.isFinal && !e.overlap && !n.overlap && r >= -250 && r <= 700 && n.endedAtMs - e.startedAtMs <= 45e3 && i.length < w) || !e) {
			t.push({
				...n,
				sourceSegmentIds: [n.id]
			});
			continue;
		}
		t[t.length - 1] = {
			...e,
			revision: e.revision + n.revision,
			text: se(e.text, n.text),
			transcriptConfidence: Math.min(e.transcriptConfidence, n.transcriptConfidence),
			endedAtMs: Math.max(e.endedAtMs, n.endedAtMs),
			isFinal: n.isFinal,
			...!n.isFinal && n.turnState ? { turnState: n.turnState } : {},
			...n.terminalState ? { terminalState: n.terminalState } : {},
			...n.finalizationReason ? { finalizationReason: n.finalizationReason } : {},
			...n.publishedAtMs === void 0 ? {} : { publishedAtMs: n.publishedAtMs },
			...n.performance ? { performance: n.performance } : {},
			sourceSegmentIds: [...i, n.id]
		};
	}
	return t;
}, k = (e) => e.replace(/\s+/g, " ").trim(), A = (e, t = "") => {
	var n;
	let r = O(e), i = [...r].reverse().find((e) => (e.sourceKind === "system" || e.role === "interviewer") && e.text.trim()), a = k(t);
	if (!i) return a;
	let o = ((n = [...r].reverse().find((e) => e.role === "candidate" && e.isFinal && e.endedAtMs <= i.startedAtMs)) == null ? void 0 : n.endedAtMs) ?? -Infinity, s = r.filter((e) => (e.sourceKind === "system" || e.role === "interviewer") && e.endedAtMs > o && e.endedAtMs <= i.endedAtMs), c = [...s].reverse().find((e) => e.isFinal), l = !i.isFinal && (!c || i.endedAtMs > c.endedAtMs) ? i : null, u = s.filter((e) => e.isFinal).slice(-4);
	l && !u.some((e) => e.id === l.id) && u.push(l);
	let d = u.map((e) => k(e.text)).filter(Boolean);
	return a && !d.some((e) => e.includes(a) || a.includes(e)) && d.push(a), d.join(" ").trim();
}, { jsx: j, jsxs: M, Fragment: N } = c();
//#endregion
//#region artifacts/cn-written-multi-screen-20261019-release/web/module-src/AnswerActionBar.tsx
function le({ manualDraft: e, latestInterviewerQuestion: t = "", screenshotTask: n, onQuickAnswer: r, onScreenshot: i, disabled: a = !1, quickAnswerStatus: o = "idle", screenshotAnswerStatus: s = "idle", screenshotOnly: c = !1, multiScreen: l = !1, pendingScreenshots: u = [], screenshotLimit: d = 4, captureBusy: f = !1, captureMessage: p = "", captureUnavailable: m = !1, onBatchAnswer: h, onRemoveScreenshot: g }) {
	let _ = o === "processing", v = s === "processing" || !!(n && ![
		"completed",
		"failed",
		"cancelled"
	].includes(n.stage)), y = v || f;
	return /* @__PURE__ */ M("section", {
		className: "answer-action-bar",
		"aria-label": "面试操作",
		children: [/* @__PURE__ */ M("div", {
			className: "answer-action-buttons",
			children: [
				c ? null : /* @__PURE__ */ M("button", {
					className: "button primary action-tile",
					"aria-label": "快答",
					disabled: a || _,
					title: e.trim() ? "根据左侧输入的问题立即回答" : t.trim() ? "根据最近一条面试官问题立即回答" : "请先输入问题或等待面试官对话同步",
					onClick: r,
					children: [/* @__PURE__ */ j("strong", { children: "快答" }), /* @__PURE__ */ j("small", { children: e.trim() ? "根据左侧问题直接生成回答" : "根据最近面试官问题回答" })]
				}),
				/* @__PURE__ */ M("button", {
					className: "button ghost action-tile",
					"aria-label": l ? "截屏" : "截屏回答",
					disabled: a || v || l && (f || m || u.length >= d),
					title: l ? "截取当前共享屏幕，稍后一起回答" : "直接截取你选择的共享屏幕并回答",
					onClick: i,
					children: [/* @__PURE__ */ j("strong", { children: l ? "截屏" : "截屏回答" }), /* @__PURE__ */ j("small", { children: l ? "保存当前画面，可继续翻页截屏" : "直接截取共享屏幕并进入回答" })]
				}),
				l ? /* @__PURE__ */ M("button", {
					className: "button primary action-tile",
					"aria-label": "回答",
					disabled: a || y || u.length === 0,
					onClick: h,
					children: [/* @__PURE__ */ j("strong", { children: "回答" }), /* @__PURE__ */ j("small", { children: "将已截取的画面一起生成回答" })]
				}) : null
			]
		}), l ? /* @__PURE__ */ M("div", {
			className: "written-screenshot-collection",
			children: [/* @__PURE__ */ M("div", {
				className: "written-screenshot-summary",
				role: "status",
				"aria-live": "polite",
				children: [/* @__PURE__ */ j("span", { children: p || `已截取 ${u.length} / ${d} 张` }), f ? /* @__PURE__ */ j("small", { children: "正在截屏…" }) : null]
			}), u.length > 0 ? /* @__PURE__ */ j("ol", {
				className: "written-screenshot-list",
				"aria-label": "待回答截图",
				children: u.map((e, t) => /* @__PURE__ */ M("li", { children: [/* @__PURE__ */ M("span", {
					title: e.name,
					children: ["截图 ", t + 1]
				}), /* @__PURE__ */ j("button", {
					type: "button",
					"aria-label": `移除截图 ${t + 1}`,
					disabled: a || y,
					onClick: () => g == null ? void 0 : g(e.requestId),
					children: "×"
				})] }, e.requestId))
			}) : null]
		}) : null]
	});
}
var ue = (e, t = 320, n = 420, r = 12) => {
	let i = Math.max(1, e - r), a = Math.max(25, t / i * 100), o = Math.min(75, 100 - n / i * 100);
	return a <= o ? {
		min: a,
		max: o
	} : {
		min: 42,
		max: 42
	};
}, de = (e, t = {
	min: 25,
	max: 75
}) => Math.min(t.max, Math.max(t.min, e)), fe = (e) => `offersteady.live.${e}.split.v1`, pe = (e) => {
	if (!e) return 42;
	try {
		let t = JSON.parse(e);
		return t.version !== 1 || typeof t.ratio != "number" || !Number.isFinite(t.ratio) || t.ratio < 25 || t.ratio > 75 ? 42 : t.ratio;
	} catch {
		return 42;
	}
}, me = (e) => JSON.stringify({
	version: 1,
	ratio: de(e)
}), he = (e = 42) => ({
	splitRatio: de(e),
	viewingAnswerId: null,
	newAnswerAvailable: !1
}), ge = (e, t, n) => t && n && t !== n && e.viewingAnswerId ? {
	...e,
	newAnswerAvailable: !0
} : e, P = /* @__PURE__ */ new Set([
	"completed",
	"failed",
	"cancelled"
]), _e = (e, t) => e ? t && t.length > e.length ? t : e : t, ve = (e, t) => {
	if (!e) return t;
	if (!t) return e;
	if (e.id !== t.id) return t.updatedAtMs >= e.updatedAtMs ? t : e;
	let n = P.has(e.status), r = P.has(t.status), i = t.revision > e.revision || t.revision === e.revision && r && !n || t.revision === e.revision && r === n && t.updatedAtMs >= e.updatedAtMs ? t : e, a = _e(e.partialText, t.partialText), o = _e(e.completedText, t.completedText);
	return {
		...i,
		...e.quickAnswerCompleted || t.quickAnswerCompleted ? { quickAnswerCompleted: !0 } : {},
		...a ? { partialText: a } : {},
		...o ? { completedText: o } : {},
		updatedAtMs: Math.max(e.updatedAtMs, t.updatedAtMs)
	};
}, ye = (e, t, n, r = !1) => {
	let i = n ? e : t, a = n ? t : e;
	return {
		...a,
		...i,
		...e.quickAnswerCompleted || t.quickAnswerCompleted ? { quickAnswerCompleted: !0 } : {},
		advice: {
			...a.advice,
			...i.advice,
			detail: n || r ? _e(e.advice.detail, t.advice.detail) ?? i.advice.detail : i.advice.detail
		}
	};
}, F = (e, t, n = {}) => {
	var r;
	let i = n.preferIncomingTask && t.activeAnswerTask && ((r = e.activeAnswerTask) == null ? void 0 : r.id) !== t.activeAnswerTask.id ? t.activeAnswerTask : ve(e.activeAnswerTask, t.activeAnswerTask), a = new Map(e.questions.map((e) => [e.id, e])), o = new Set(t.questions.map((e) => e.id)), s = e.activeAnswerTask, c = t.activeAnswerTask, l = !!(s && c && s.id === c.id), u = !!(s && P.has(s.status)), d = !!(c && P.has(c.status)), f = s && (i == null ? void 0 : i.id) === s.id && (!c || c.id !== s.id || s.revision > c.revision || u && !d || s.revision === c.revision && u === d && s.updatedAtMs > c.updatedAtMs) ? (s == null ? void 0 : s.questionId) ?? null : null, p = l && !(d && !u) ? (s == null ? void 0 : s.questionId) ?? null : null, m = t.questions.map((e) => {
		let t = a.get(e.id);
		return t ? ye(t, e, e.id === f, e.id === p) : e;
	}), h = e.questions.filter((e) => !o.has(e.id)), g = [...m, ...h];
	if (i) {
		let e = g.findIndex((e) => e.id === i.questionId);
		e > 0 && g.unshift(...g.splice(e, 1));
	}
	return {
		questions: g,
		activeAnswerTask: i
	};
}, be = (e) => e.replace(/\s+/g, "").length > 0, xe = (e, t) => {
	var n, r, i;
	let a = e.transcripts.some((e) => e.sessionId !== t) || !!(e.pendingQuestion && e.pendingQuestion.sessionId !== t) || !!(e.autoAnswerQuestion && e.autoAnswerQuestion.sessionId !== t) || !!(e.degradation && e.degradation.sessionId !== t);
	return {
		...e,
		transcripts: e.transcripts.filter((e) => e.sessionId === t),
		pendingQuestion: ((n = e.pendingQuestion) == null ? void 0 : n.sessionId) === t ? e.pendingQuestion : null,
		autoAnswerQuestion: ((r = e.autoAnswerQuestion) == null ? void 0 : r.sessionId) === t ? e.autoAnswerQuestion : null,
		degradation: ((i = e.degradation) == null ? void 0 : i.sessionId) === t ? e.degradation : null,
		runtimeNotice: a ? null : e.runtimeNotice
	};
}, Se = (e, t, n) => {
	let r = n ? xe(e, n) : e, i = n ? xe(t, n) : t, a = new Map(r.transcripts.filter((e) => be(e.text)).map((e) => [e.id, e]));
	for (let e of i.transcripts) be(e.text) && ae(a.get(e.id), e) && a.set(e.id, e);
	return {
		...i,
		transcripts: D([...a.values()])
	};
}, Ce = 6e4, we = (e, t) => Ee(e) ? Ce : t <= 0 ? 0 : [
	2e3,
	4e3,
	8e3,
	15e3
][Math.min(t - 1, 3)], Te = (e, t) => t === "stream-snapshot" ? 0 : Math.max(0, e), Ee = (e) => e === 401 || e === 403 || e === 404 || e === 409 || e === 410;
//#endregion
//#region \0@oxc-project+runtime@0.137.0/helpers/esm/typeof.js
function De(e) {
	"@babel/helpers - typeof";
	return De = typeof Symbol == "function" && typeof Symbol.iterator == "symbol" ? function(e) {
		return typeof e;
	} : function(e) {
		return e && typeof Symbol == "function" && e.constructor === Symbol && e !== Symbol.prototype ? "symbol" : typeof e;
	}, De(e);
}
//#endregion
//#region \0@oxc-project+runtime@0.137.0/helpers/esm/toPrimitive.js
function I(e, t) {
	if (De(e) != "object" || !e) return e;
	var n = e[Symbol.toPrimitive];
	if (n !== void 0) {
		var r = n.call(e, t || "default");
		if (De(r) != "object") return r;
		throw TypeError("@@toPrimitive must return a primitive value.");
	}
	return (t === "string" ? String : Number)(e);
}
//#endregion
//#region \0@oxc-project+runtime@0.137.0/helpers/esm/toPropertyKey.js
function Oe(e) {
	var t = I(e, "string");
	return De(t) == "symbol" ? t : t + "";
}
//#endregion
//#region \0@oxc-project+runtime@0.137.0/helpers/esm/defineProperty.js
function L(e, t, n) {
	return (t = Oe(t)) in e ? Object.defineProperty(e, t, {
		value: n,
		enumerable: !0,
		configurable: !0,
		writable: !0
	}) : e[t] = n, e;
}
//#endregion
//#region ../../../../../private/tmp/offersteady-cn-written-multi-screen/apps/web/src/live-session-leader.ts
var ke = class {
	constructor(e, t, n = Date.now) {
		L(this, "channel", void 0), L(this, "pageId", void 0), L(this, "now", void 0), L(this, "leader", !1), L(this, "epoch", 0), L(this, "leaderPageId", null), L(this, "leaderEpoch", 0), L(this, "lastLeaderAt", 0), L(this, "eligible", !0), L(this, "electionTimer", null), L(this, "heartbeatTimer", null), L(this, "watchdogTimer", null), L(this, "callbacks", null), L(this, "onMessage", (e) => {
			let t = e.data;
			if (!(!t || t.pageId === this.pageId)) {
				if (t.type === "probe") {
					this.leader && !this.eligible ? (this.post("release"), this.setLeader(!1), this.leaderPageId === this.pageId && (this.leaderPageId = null)) : this.eligible && this.leader && this.post("leader");
					return;
				}
				if (t.type === "release") {
					this.eligible && !this.leader && t.epoch >= this.leaderEpoch && (this.leaderPageId = null, this.leaderEpoch = t.epoch, this.lastLeaderAt = 0, this.becomeLeader());
					return;
				}
				if (t.type === "leader") {
					if (this.eligible && this.leader && this.pageId < t.pageId) {
						this.post("leader");
						return;
					}
					(!this.leader || t.pageId < this.pageId || t.epoch > this.epoch) && (this.leaderPageId = t.pageId, this.leaderEpoch = t.epoch, this.lastLeaderAt = this.now(), this.setLeader(!1));
					return;
				}
				if (t.type === "state") {
					var n;
					if (t.pageId !== this.leaderPageId || t.epoch < this.leaderEpoch || !t.state) return;
					this.lastLeaderAt = this.now(), (n = this.callbacks) == null || n.onState(t.state);
				}
			}
		}), this.channel = e, this.pageId = t, this.now = n;
	}
	start(e, t = !0) {
		this.callbacks = e, this.eligible = t, this.channel.addEventListener("message", this.onMessage), this.eligible && this.requestElection(), this.watchdogTimer = window.setInterval(() => {
			this.eligible && !this.leader && this.now() - this.lastLeaderAt > 5e3 && this.becomeLeader();
		}, 1e3);
	}
	setEligible(e) {
		if (this.eligible !== e) {
			if (this.eligible = e, !e) {
				this.electionTimer !== null && (window.clearTimeout(this.electionTimer), this.electionTimer = null), !this.leader && this.leaderPageId === this.pageId && (this.leaderPageId = null);
				return;
			}
			this.leader || (this.lastLeaderAt = 0, this.requestElection());
		}
	}
	publishState(e) {
		this.leader && this.post("state", e);
	}
	isLeader() {
		return this.leader;
	}
	stop() {
		this.leader && this.post("release"), this.setLeader(!1), this.electionTimer !== null && window.clearTimeout(this.electionTimer), this.watchdogTimer !== null && window.clearInterval(this.watchdogTimer), this.channel.removeEventListener("message", this.onMessage), this.channel.close(), this.callbacks = null;
	}
	becomeLeader() {
		this.eligible && (this.epoch = Math.max(this.epoch + 1, this.now()), this.leaderPageId = this.pageId, this.leaderEpoch = this.epoch, this.lastLeaderAt = this.now(), this.setLeader(!0), this.post("leader"), this.heartbeatTimer !== null && window.clearInterval(this.heartbeatTimer), this.heartbeatTimer = window.setInterval(() => this.post("leader"), 2e3));
	}
	requestElection() {
		this.eligible && (this.post("probe"), this.electionTimer !== null && window.clearTimeout(this.electionTimer), this.electionTimer = window.setTimeout(() => {
			this.electionTimer = null, this.eligible && this.now() - this.lastLeaderAt >= 120 && this.becomeLeader();
		}, 120));
	}
	setLeader(e) {
		var t;
		this.leader !== e && (this.leader = e, !e && this.heartbeatTimer !== null && (window.clearInterval(this.heartbeatTimer), this.heartbeatTimer = null), (t = this.callbacks) == null || t.onLeadershipChange(e));
	}
	post(e, t) {
		this.channel.postMessage({
			type: e,
			pageId: this.pageId,
			epoch: this.epoch,
			sentAt: this.now(),
			...t ? { state: t } : {}
		});
	}
}, Ae = (e, t) => typeof BroadcastChannel == "function" ? new ke(new BroadcastChannel(e), t) : null, je = 15e3, Me = (e, t) => (e ?? 0) >= t - 5e3, Ne = [{
	id: "douyin",
	label: "抖音号",
	account: "面试稳AI助手"
}, {
	id: "xiaohongshu",
	label: "小红书号",
	account: "面试稳AI助手"
}], Pe = (e) => e === "written" ? a.writtenExams : a.app, Fe = {
	id: "empty-live-question",
	askedAt: "等待中",
	text: "等待面试问题",
	input: "manual",
	status: "listening",
	advice: {
		outline: [],
		detail: "当前还没有来自后端的面试问题记录。",
		sourceTypes: [],
		inference: "",
		uncertain: !0,
		provenance: {
			selectionRevision: 0,
			usedSources: []
		}
	}
}, Ie = "未能识别到面试官的问题", Le = (e) => {
	var t;
	return A(e.transcripts, ((t = e.pendingQuestion) == null ? void 0 : t.text) ?? "");
};
function Re() {
	let e = "(min-width: 721px)", [t, n] = v(() => typeof window.matchMedia == "function" ? window.matchMedia(e).matches : window.innerWidth > 720);
	return g(() => {
		var t;
		if (typeof window.matchMedia != "function") {
			let e = () => n(window.innerWidth > 720);
			return window.addEventListener("resize", e), () => window.removeEventListener("resize", e);
		}
		let r = window.matchMedia(e), i = () => n(r.matches);
		return i(), (t = r.addEventListener) == null || t.call(r, "change", i), () => {
			var e;
			return (e = r.removeEventListener) == null ? void 0 : e.call(r, "change", i);
		};
	}, []), t;
}
function ze({ brand: s, accountMenu: c }) {
	var p, y, b, x, re, S, ie, ae, oe;
	let { id: C = "demo" } = i(), { state: w, setState: T } = o(), se = r(), ce = fe(C), [E, D] = v(() => {
		var e;
		return he(pe(typeof ((e = window.sessionStorage) == null ? void 0 : e.getItem) == "function" ? window.sessionStorage.getItem(ce) : null));
	}), [O, k] = v({
		manualDraft: "",
		screenshotTask: null,
		quickAnswerStatus: "idle",
		quickAnswerMessage: "",
		screenshotAnswerStatus: "idle",
		webSearchEnabled: !1
	}), [A, N] = v(""), [P, _e] = v(!1), [ve, ye] = v([]), [be, Ce] = v(!1), [De, I] = v(""), [Oe, L] = v(!1), [ke, ze] = v(null), [Be, Ve] = v(""), R = _([]), z = _(null), B = _(0), He = _(!1), V = _(!1), Ue = _([]), We = _(null), Ge = _(/* @__PURE__ */ new Set()), [Ke, qe] = v(!1), [Je, Ye] = v(""), [H, Xe] = v("claiming"), [Ze, Qe] = v(null), [$e, et] = v(0), [tt, nt] = v(null), [rt, it] = v(!1), [at, ot] = v(!1), [st, ct] = v({
		min: 25,
		max: 75
	}), [lt, ut] = v("answer"), dt = _(null), U = Re(), ft = _(/* @__PURE__ */ new Set()), pt = _(/* @__PURE__ */ new Set()), mt = _((p = w.questions[0]) == null ? void 0 : p.id), W = _(null), G = _(null), K = _(null), q = _(/* @__PURE__ */ new Set()), ht = _(/* @__PURE__ */ new Set()), gt = _(/* @__PURE__ */ new Set()), _t = _(0), vt = (e) => q.current.has(e.id) || e.clickedAtMs !== void 0 && gt.current.has(e.clickedAtMs), yt = _(() => void 0), J = _(null), bt = _(/* @__PURE__ */ new Set()), xt = _(/* @__PURE__ */ new Set()), Y = _(!1), St = _(Date.now()), Ct = _(((y = globalThis.crypto) == null || (b = y.randomUUID) == null ? void 0 : b.call(y)) ?? `page-${Date.now()}-${Math.random().toString(36).slice(2)}`), X = w.interviews.find((e) => e.id === C), Z = (X == null ? void 0 : X.sessionMode) === "written", wt = (X == null ? void 0 : X.title) ?? "本场面试", Tt = ((X == null ? void 0 : X.interviewLanguage) ?? "zh-CN") === "en-US" ? "English Interview" : "中文面试", Et = w.questions[0] ?? Fe, Q = O.screenshotTask, $ = (e) => k((t) => ({
		...t,
		screenshotTask: e,
		screenshotAnswerStatus: e ? e.stage === "completed" ? "success" : e.stage === "failed" ? "failed" : e.stage === "cancelled" ? "cancelled" : "processing" : t.screenshotAnswerStatus ?? "idle"
	})), Dt = (t) => {
		for (let n of t) e.cancelDesktopShortcutScreenshot(n.requestId).catch(() => void 0);
	}, Ot = (e = !0) => {
		var t, n;
		B.current += 1, (t = z.current) == null || t.abort(), z.current = null, V.current && ((n = W.current) == null || n.abort()), V.current = !1, Dt([...R.current, ...Ue.current]), R.current = [], Ue.current = [], e && (ye([]), Ce(!1), I(""), L(!1));
	};
	g(() => (He.current = !1, _e(!1), () => Ot(!1)), [C]), g(() => {
		H === "replaced" && Ot();
	}, [H]), g(() => {
		if (!Z) return;
		let t = new AbortController();
		return ze(null), Ve(""), (async () => {
			try {
				if (!e.getScreenshotCapturePolicy) throw Error("多屏截屏暂不可用，请稍后重试。");
				let n = await e.getScreenshotCapturePolicy(t.signal);
				if (!Number.isInteger(n.maxImagesPerTask) || n.maxImagesPerTask < 1) throw Error("无法读取截屏数量限制，请刷新后重试。");
				t.signal.aborted || ze(Math.min(4, n.maxImagesPerTask));
			} catch (e) {
				t.signal.aborted || Ve(e instanceof Error ? e.message : "无法读取截屏设置，请刷新后重试。");
			}
		})(), () => t.abort();
	}, [C, Z]);
	let kt = w.contextSelections[C] ?? {
		sessionId: C,
		resumeSourceId: null,
		jobDescriptionSourceId: null,
		knowledgeSourceIds: [],
		revision: 0,
		confirmedAtMs: null
	}, At = ne(ee(w.librarySources, w.account.id).filter(te), kt);
	g(() => {
		var e;
		typeof ((e = window.sessionStorage) == null ? void 0 : e.setItem) == "function" && window.sessionStorage.setItem(ce, me(E.splitRatio));
	}, [ce, E.splitRatio]), g(() => {
		if (!U) return;
		let e = () => {
			var e;
			let t = ((e = dt.current) == null ? void 0 : e.getBoundingClientRect().width) ?? 0;
			if (!t) return;
			let n = t < 900 ? ue(t, 240, 300) : ue(t);
			ct(n), D((e) => ({
				...e,
				splitRatio: de(e.splitRatio, n)
			}));
		};
		e(), window.addEventListener("resize", e);
		let t = typeof ResizeObserver == "function" ? new ResizeObserver(e) : null;
		return dt.current && (t == null || t.observe(dt.current)), () => {
			window.removeEventListener("resize", e), t == null || t.disconnect();
		};
	}, [U]), g(() => {
		var e;
		let t = (e = w.questions[0]) == null ? void 0 : e.id;
		!U && mt.current && t && mt.current !== t && ut("answer"), D((e) => ge(e, mt.current, t)), mt.current = t;
	}, [U, w.questions]), g(() => {
		!U && w.activeAnswerTask && ["pending", "generating"].includes(w.activeAnswerTask.status) && ut("answer");
	}, [
		U,
		(x = w.activeAnswerTask) == null ? void 0 : x.id,
		(re = w.activeAnswerTask) == null ? void 0 : re.status
	]), g(() => () => {
		var e, t;
		(e = W.current) == null || e.abort(), (t = G.current) == null || t.abort();
	}, []), g(() => {
		T((e) => {
			var t;
			return {
				...e,
				speaker: xe(e.speaker, C),
				activeAnswerTask: ((t = e.activeAnswerTask) == null ? void 0 : t.interviewId) === C ? e.activeAnswerTask : null
			};
		});
	}, [C, T]), g(() => {
		let t = new AbortController(), n = !1, r = !1, i = async () => {
			if (!(n || r || document.visibilityState !== "visible")) {
				r = !0;
				try {
					let r = await l((t) => e.loadInterviewWorkspace(C, t), t.signal);
					if (n) return;
					r.activeAnswerTask && vt(r.activeAnswerTask) && q.current.add(r.activeAnswerTask.questionId), T((e) => ({
						...e,
						...F({
							questions: e.questions,
							activeAnswerTask: e.activeAnswerTask
						}, {
							questions: r.questions.filter((e) => !q.current.has(e.id)),
							activeAnswerTask: r.activeAnswerTask && !vt(r.activeAnswerTask) ? r.activeAnswerTask : null
						})
					}));
				} catch {} finally {
					r = !1;
				}
			}
		};
		i();
		let a = () => {
			document.visibilityState === "visible" && i();
		};
		return document.addEventListener("visibilitychange", a), window.addEventListener("focus", a), () => {
			n = !0, t.abort(), document.removeEventListener("visibilitychange", a), window.removeEventListener("focus", a);
		};
	}, [C, T]), g(() => {
		if (H === "replaced") return;
		let t = new AbortController(), n = !1, r = async () => {
			try {
				let r = await l((t) => e.getInterviewIdleStatus(C, t), t.signal);
				if (n) return;
				nt(r), r.state === "ended" && (T((e) => ({
					...e,
					captureState: "ready",
					interviews: e.interviews.map((e) => e.id === C ? {
						...e,
						status: "ended"
					} : e)
				})), se(a.review(C), { replace: !0 }));
			} catch {}
		};
		r();
		let i = window.setInterval(() => void r(), 15e3);
		return () => {
			n = !0, t.abort(), window.clearInterval(i);
		};
	}, [
		C,
		se,
		H,
		T
	]), g(() => {
		if (H === "replaced") return;
		let t = new AbortController(), n = !1, r = !1, i = async () => {
			if (!(n || r || Y.current || document.visibilityState !== "visible")) {
				r = !0;
				try {
					let r = await l((t) => e.loadDesktopShortcutScreenshotUpdates(C, t), t.signal);
					if (n || r.length === 0) return;
					let i = r[r.length - 1], a = bt.current.has(i.requestId);
					(i.status === "requested" || i.status === "processing") && !a ? (J.current = i.requestId, $(i.screenshotTask)) : a || (bt.current.add(i.requestId), J.current === i.requestId && (J.current = null), i.status === "completed" ? k((e) => ({
						...e,
						screenshotTask: null,
						screenshotAnswerStatus: "success"
					})) : $(i.screenshotTask));
					let o = r.flatMap((e) => e.result ? [e.result] : []);
					T((e) => {
						if (o.length === 0) return e;
						let t = o.reduce((e, t) => t.task.updatedAtMs > e.task.updatedAtMs ? t : e);
						return {
							...e,
							...F({
								questions: e.questions,
								activeAnswerTask: e.activeAnswerTask
							}, {
								questions: o.map((e) => e.question),
								activeAnswerTask: t.task
							})
						};
					});
				} catch {} finally {
					r = !1;
				}
			}
		};
		i();
		let a = window.setInterval(() => void i(), je);
		return () => {
			n = !0, t.abort(), window.clearInterval(a);
		};
	}, [
		C,
		H,
		T
	]), g(() => {
		let t = !1, n = null, r = null, i = null, a = 0, o = null, s = 0, c = !1, u = !1, d = !1, f = !1, p = null, m = new AbortController(), h = Ae(`offersteady:live-session:${w.account.id}:${C}`, Ct.current), g = h === null, _ = (e) => {
			if (typeof e == "object" && e && "status" in e && typeof e.status == "number") return e.status;
			let t = e instanceof Error ? e.message.match(/[（(](\d{3})[）)]/) : null;
			return t ? Number(t[1]) : null;
		}, v = () => {
			var e, r;
			t || (t = !0, Y.current = !1, Xe("replaced"), N(""), m.abort(), p == null || p.abort(), (e = G.current) == null || e.abort(), (r = W.current) == null || r.abort(), o !== null && window.clearTimeout(o), n !== null && window.clearInterval(n));
		}, y = (e, n = !0) => {
			if (t) return;
			let r = e.shortcutScreenshotUpdate, i = r == null ? void 0 : r.notificationId;
			if (r && i && !xt.current.has(i) && !bt.current.has(r.requestId) && Me(r.acceptedAtMs, St.current) && (xt.current.add(i), J.current = r.requestId, $(r.screenshotTask)), r && r.acceptedAtMs === void 0) {
				let e = bt.current.has(r.requestId);
				(r.status === "requested" || r.status === "processing") && !e ? (J.current = r.requestId, $(r.screenshotTask)) : e || (bt.current.add(r.requestId), J.current === r.requestId && (J.current = null), r.status === "completed" ? k((e) => ({
					...e,
					screenshotTask: null,
					screenshotAnswerStatus: "success"
				})) : r.status === "cancelled" ? k((e) => ({
					...e,
					screenshotTask: null,
					screenshotAnswerStatus: "cancelled"
				})) : $(r.screenshotTask));
			}
			T((t) => {
				let n = [e.answerUpdate, r == null ? void 0 : r.result].filter((e) => !!(e && !vt(e.task))), i = n.length > 0 ? n.reduce((e, t) => t.task.updatedAtMs > e.task.updatedAtMs ? t : e) : null, a = i ? F({
					questions: t.questions,
					activeAnswerTask: t.activeAnswerTask
				}, {
					questions: n.map((e) => e.question),
					activeAnswerTask: i.task
				}) : {
					questions: t.questions,
					activeAnswerTask: t.activeAnswerTask
				};
				return {
					...t,
					...a,
					speaker: Se(t.speaker, e.speaker, C),
					...e.captureState ? { captureState: e.captureState } : {}
				};
			}), n && (h == null || h.publishState(e));
		}, b = async () => {
			if (!g) return !1;
			try {
				let t = Date.now();
				if (!r || t - a >= 3e4) {
					let n = await l((t) => e.getDesktopDeviceBinding(C, t));
					n != null && n.bindingId && (r = n.bindingId), a = t;
				}
				let n = await l((t) => e.sendDesktopSessionHeartbeat({
					interviewId: C,
					bindingId: r,
					page: "live",
					pageInstanceId: Ct.current
				}, t));
				return n.pageInstanceId !== Ct.current || n.leaseGeneration < 1 ? (v(), !1) : (i = n.leaseGeneration, Xe("active"), !0);
			} catch (e) {
				return Ee(_(e)) ? (v(), !1) : (r = null, !1);
			}
		}, ee = async () => {
			if (!g || f || t || document.visibilityState !== "visible" || i === null) return !1;
			f = !0;
			try {
				return y(await l((t) => e.loadRealtimeSession(C, t, {
					pageInstanceId: Ct.current,
					leaseGeneration: i
				}))), !0;
			} catch {
				return !1;
			} finally {
				f = !1;
			}
		}, te = (e = null) => {
			if (t || m.signal.aborted) return;
			o !== null && window.clearTimeout(o), c = Ee(e);
			let n = we(e, s);
			s += 1, o = window.setTimeout(() => {
				o = null, c = !1, ne();
			}, n);
		}, ne = async () => {
			if (!g || u || t || m.signal.aborted || i === null) return;
			let n = i, r = new AbortController();
			p = r;
			let a = () => r.abort();
			m.signal.addEventListener("abort", a, { once: !0 }), u = !0;
			try {
				await l((t) => e.subscribeRealtimeSession(C, (e, t) => {
					(t == null ? void 0 : t.type) === "snapshot" && (d = !0, Y.current = !0, c = !1, s = Te(s, "stream-snapshot"), o !== null && (window.clearTimeout(o), o = null)), y(e);
				}, t, {
					pageInstanceId: Ct.current,
					leaseGeneration: n
				}), r.signal), d = !1, Y.current = !1, !t && !m.signal.aborted && te();
			} catch (e) {
				if (t || m.signal.aborted) return;
				d = !1, Y.current = !1;
				let n = _(e);
				if (Ee(n)) {
					var f;
					(f = window.sessionStorage) == null || f.removeItem(`offersteady:realtime-cursor:${C}`), n === 409 || n === 410 ? v() : (N("当前面试会话已失效，请从面试首页重新进入。"), se(Pe(X == null ? void 0 : X.sessionMode), { replace: !0 }));
					return;
				}
				await ee() && (s = Te(s, "fallback-snapshot")), te(n);
			} finally {
				u = !1, m.signal.removeEventListener("abort", a), p === r && (p = null);
			}
		};
		h == null || h.start({
			onLeadershipChange: (e) => {
				if (g = e, !e) {
					d = !1, Y.current = !1, p == null || p.abort(), p = null, o !== null && (window.clearTimeout(o), o = null);
					return;
				}
				b().then((e) => {
					e && ne();
				});
			},
			onState: (e) => {
				d = !0, Y.current = !0, y(e, !1);
			}
		}, document.visibilityState === "visible"), n = window.setInterval(() => void b(), 15e3);
		let x = () => {
			t || !g || document.visibilityState !== "visible" || (b(), !c && !d && !u && (o !== null && (window.clearTimeout(o), o = null), s = 0, ne()));
		}, re = () => {
			h == null || h.setEligible(document.visibilityState === "visible"), document.visibilityState === "visible" && x();
		}, S = () => h == null ? void 0 : h.setEligible(!1), ie = () => {
			h == null || h.setEligible(document.visibilityState === "visible"), document.visibilityState === "visible" && x();
		};
		return document.addEventListener("visibilitychange", re), window.addEventListener("pagehide", S), window.addEventListener("pageshow", ie), window.addEventListener("focus", x), window.addEventListener("online", x), g && b().then((e) => {
			!e || t || ne();
		}), () => {
			t = !0, Y.current = !1, m.abort(), p == null || p.abort(), o !== null && window.clearTimeout(o), n !== null && window.clearInterval(n), h == null || h.stop(), document.removeEventListener("visibilitychange", re), window.removeEventListener("pagehide", S), window.removeEventListener("pageshow", ie), window.removeEventListener("focus", x), window.removeEventListener("online", x);
		};
	}, [
		C,
		se,
		$e,
		T,
		w.account.id
	]);
	let jt = {
		...Et.advice,
		detail: At.length ? Et.advice.detail : "当前没有选择个人资料。请使用通用结构组织回答，并只补充你能够核对的真实经历、职责和结果。",
		sourceTypes: At.map((e) => e.kind === "resume" ? "简历" : e.kind === "jd" ? "JD" : "知识库"),
		inference: "",
		uncertain: At.length === 0,
		provenance: {
			selectionRevision: kt.revision,
			usedSources: At.map((e) => ({
				sourceId: e.id,
				sourceVersion: e.version,
				displayName: e.displayName,
				kind: e.kind
			}))
		}
	}, Mt = async () => {
		try {
			let t = await e.loadState();
			T((e) => ({
				...e,
				billing: t.billing
			}));
		} catch {}
	}, Nt = (e, t) => ({
		id: `answer:${e.id}:${Date.now()}`,
		interviewId: C,
		userId: w.account.id,
		billingUsageId: t,
		questionId: e.id,
		question: e.text,
		revision: 1,
		status: "generating",
		partialText: "正在整理回答结构…",
		updatedAtMs: Date.now()
	}), Pt = (e, t, n = "manual") => ({
		...Et,
		id: t,
		text: e,
		input: n,
		askedAt: "刚刚",
		status: "generating",
		advice: {
			...jt,
			detail: "正在调用当前对话模型生成回答…",
			outline: [],
			inference: "",
			uncertain: At.length === 0
		}
	}), Ft = (e, t = "回答生成失败，请稍后重试。") => ({
		...e,
		status: "failed",
		advice: {
			...e.advice,
			outline: [],
			detail: e.quickAnswerCompleted ? e.advice.detail : t,
			inference: "",
			uncertain: !0
		}
	}), It = async (t, n, r) => {
		var i, a, o;
		let s = t.trim();
		if (!s) return;
		let c = Math.max((r == null ? void 0 : r.clickedAtMs) ?? Date.now(), _t.current + 1), u = O.webSearchEnabled === !0, d = u ? "web" : "local", f = (r == null ? void 0 : r.triggerMode) === "auto" ? "auto" : "manual", p = `${f}:${C}:${d}:${(r == null ? void 0 : r.triggerMode) === "auto" ? r.questionId : s}`;
		if (ft.current.has(p)) return;
		_t.current = c;
		let m = `${f}:${C}:${d}:${((i = globalThis.crypto) == null || (a = i.randomUUID) == null ? void 0 : a.call(i)) ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`}`;
		ft.current.add(p), N(""), k((e) => ({
			...e,
			quickAnswerStatus: "processing",
			quickAnswerMessage: ""
		}));
		let h = n ?? `manual-pending-${m}`, g = Pt(s, h, (r == null ? void 0 : r.triggerMode) === "auto" ? "desktop-audio" : "manual"), _ = {
			id: `pending:${h}`,
			interviewId: C,
			userId: w.account.id,
			billingUsageId: `pending:${h}`,
			questionId: h,
			question: s,
			revision: 1,
			status: "generating",
			partialText: "正在调用当前对话模型生成回答…",
			clickedAtMs: c,
			updatedAtMs: Date.now()
		};
		(o = G.current) == null || o.abort(), K.current && ft.current.delete(K.current.command);
		let v = new AbortController(), y = {
			controller: v,
			command: p,
			webSearchEnabled: u,
			task: _,
			question: g,
			pendingId: h
		};
		G.current = v, K.current = y;
		let b = () => K.current === y && !v.signal.aborted;
		T((e) => ({
			...e,
			questions: n ? e.questions.map((e) => e.id === n ? g : e) : [g, ...e.questions],
			activeAnswerTask: _
		})), k((e) => ({
			...e,
			manualDraft: ""
		})), D((e) => ({
			...e,
			viewingAnswerId: null,
			newAnswerAvailable: !1
		}));
		let ee = null, te, ne = !1, x = null, re = (t) => {
			if (!b()) return;
			T((e) => ({
				...e,
				...F({
					questions: e.questions.filter((e) => e.id !== h && e.id !== t.result.question.id),
					activeAnswerTask: e.activeAnswerTask
				}, {
					questions: [t.result.question],
					activeAnswerTask: t.result.task
				}, { preferIncomingTask: !0 })
			}));
			let n = t.result.task.partialText ?? t.result.task.completedText ?? "";
			if (t.event.type === "chunk" && n.trim() && t.result.task.clickedAtMs && e.acknowledgeAnswerFirstRender) {
				let r = () => {
					var r;
					return (r = e.acknowledgeAnswerFirstRender) == null ? void 0 : r.call(e, {
						interviewId: C,
						taskId: t.result.task.id,
						clickedAtMs: t.result.task.clickedAtMs,
						...t.event.receivedAtMs === void 0 ? {} : { browserEventReceiveAtMs: t.event.receivedAtMs },
						browserRenderAtMs: Date.now(),
						renderedTextLength: n.length,
						timing: t.event.timing
					});
				};
				typeof requestAnimationFrame == "function" ? requestAnimationFrame(r) : window.setTimeout(r, 0);
			}
		}, S = () => {
			if (x !== null && window.clearTimeout(x), x = null, !ee) return;
			let e = ee;
			ee = null, re(e);
		};
		try {
			let t = await l((t) => e.submitManualAnswer({
				interviewId: C,
				question: s,
				idempotencyKey: m,
				...r,
				clickedAtMs: c,
				webSearchEnabled: u
			}, t, (e) => {
				if (!b()) return;
				e.event.type === "quick-completed" && S(), y.task = e.result.task, y.question = e.result.question, te ??= e.event.timing, ee = te && !e.event.timing ? {
					...e,
					event: {
						...e.event,
						timing: te
					}
				} : e;
				let t = e.event.type === "chunk" && !ne;
				e.event.type === "chunk" && (ne = !0), t || [
					"quick-completed",
					"completed",
					"failed",
					"cancelled"
				].includes(e.event.type) ? S() : x === null && (x = window.setTimeout(S, 16));
			}), v.signal);
			if (!b()) return;
			S(), T((e) => ({
				...e,
				...F({
					questions: e.questions.filter((e) => e.id !== h && e.id !== t.question.id),
					activeAnswerTask: e.activeAnswerTask
				}, {
					questions: [t.question],
					activeAnswerTask: t.task
				}, { preferIncomingTask: !0 })
			})), k((e) => ({
				...e,
				quickAnswerStatus: t.task.status === "failed" ? "failed" : t.task.status === "completed" ? "success" : t.task.status === "cancelled" ? "cancelled" : "processing",
				quickAnswerMessage: t.task.status === "failed" ? t.task.partialText ?? "快答失败，可重试" : ""
			})), t.task.status === "completed" && Mt();
		} catch (e) {
			if (!b() || e instanceof DOMException && e.name === "AbortError" || e instanceof Error && e.message === "请求已取消") return;
			let t = e instanceof Error ? e.message : "回答生成失败，请稍后重试。";
			S(), N(t), k((e) => ({
				...e,
				quickAnswerStatus: "failed",
				quickAnswerMessage: t
			})), T((e) => {
				var n, r;
				return {
					...e,
					questions: e.questions.map((e) => e.id === h || e.id === y.task.questionId ? Ft(e, t) : e),
					activeAnswerTask: ((n = e.activeAnswerTask) == null ? void 0 : n.questionId) === h || ((r = e.activeAnswerTask) == null ? void 0 : r.id) === y.task.id ? {
						...e.activeAnswerTask,
						status: "failed",
						partialText: y.task.quickAnswerCompleted ? y.task.partialText ?? y.question.advice.detail : t,
						updatedAtMs: Date.now()
					} : e.activeAnswerTask
				};
			});
		} finally {
			x !== null && window.clearTimeout(x), G.current === v && (G.current = null), K.current === y && (K.current = null, ft.current.delete(p));
		}
	}, Lt = () => {
		var t;
		let n = !O.webSearchEnabled;
		k((e) => ({
			...e,
			webSearchEnabled: n
		}));
		let r = K.current;
		n || !(r != null && r.webSearchEnabled) || [
			"completed",
			"failed",
			"cancelled"
		].includes(r.task.status) || (K.current = null, G.current = null, ft.current.delete(r.command), q.current.add(r.task.id), q.current.add(r.task.questionId), q.current.add(r.pendingId), !r.task.billingUsageId.startsWith("pending:") && (t = r.task.partialText) != null && t.trim() && ht.current.add(r.task.questionId), r.task.clickedAtMs !== void 0 && gt.current.add(r.task.clickedAtMs), r.controller.abort(), k((e) => ({
			...e,
			quickAnswerStatus: "idle",
			quickAnswerMessage: ""
		})), N("联网已关闭，可继续使用普通快答。"), T((e) => {
			var t, n;
			return {
				...e,
				activeAnswerTask: ((t = e.activeAnswerTask) == null ? void 0 : t.id) === r.task.id || ((n = e.activeAnswerTask) == null ? void 0 : n.questionId) === r.pendingId ? {
					...r.task,
					status: "cancelled",
					updatedAtMs: Date.now()
				} : e.activeAnswerTask,
				questions: e.questions.map((e) => e.id === r.task.questionId || e.id === r.pendingId ? {
					...r.question,
					status: "cancelled"
				} : e)
			};
		}), r.task.billingUsageId.startsWith("pending:") || l((t) => e.cancelAnswer({
			interviewId: C,
			answerTaskId: r.task.id,
			expectedRevision: 1,
			idempotencyKey: `cancel-web:${r.task.id}`
		}, r.task, t)).then(() => Mt()).catch(() => {
			K.current || N("联网已关闭，旧任务取消确认失败，请稍后核对回答状态。");
		}));
	};
	g(() => {
		let e = w.speaker.autoAnswerQuestion, t = (X == null ? void 0 : X.autoAnswerEnabledAtMs) ?? null, n = !!(w.activeAnswerTask && ["pending", "generating"].includes(w.activeAnswerTask.status));
		!(X != null && X.autoAnswerEnabled) || !t || !e || (e.createdAtMs ?? 0) < t || e.answerTaskId || e.state !== "auto-confirmed" || w.speaker.mode !== "dual-channel" || !["capturing", "reconnecting"].includes(w.captureState) || H !== "active" || n || pt.current.has(e.id) || (pt.current.add(e.id), It(e.text, void 0, {
			questionId: e.id,
			questionRevision: e.revision,
			clickedAtMs: Date.now(),
			prefetchRevision: e.revision,
			triggerMode: "auto"
		}));
	}, [
		X == null ? void 0 : X.autoAnswerEnabled,
		X == null ? void 0 : X.autoAnswerEnabledAtMs,
		H,
		(S = w.activeAnswerTask) == null ? void 0 : S.id,
		(ie = w.activeAnswerTask) == null ? void 0 : ie.status,
		w.captureState,
		(ae = w.speaker.autoAnswerQuestion) == null ? void 0 : ae.id,
		(oe = w.speaker.autoAnswerQuestion) == null ? void 0 : oe.answerTaskId,
		w.speaker.mode
	]);
	let Rt = async (t) => {
		if (!(at || H === "replaced")) {
			ot(!0), N("");
			try {
				let n = await l((n) => e.updateInterviewAutoAnswer(C, t, n));
				pt.current.clear(), T((e) => ({
					...e,
					interviews: e.interviews.map((e) => e.id === C ? {
						...e,
						...n
					} : e)
				}));
			} catch (e) {
				N(e instanceof Error ? e.message : "自动回答设置保存失败，请稍后重试。");
			} finally {
				ot(!1);
			}
		}
	}, zt = () => Le(w.speaker), Bt = zt(), Vt = () => {
		let e = zt(), t = O.manualDraft.trim() || e;
		if (!t) {
			N(Ie);
			return;
		}
		let n = [...w.speaker.transcripts].reverse().find((e) => e.sourceKind === "system" || e.role === "interviewer"), r = w.speaker.pendingQuestion, i = (r == null ? void 0 : r.revision) ?? (n == null ? void 0 : n.revision), a = (r == null ? void 0 : r.id) ?? (n == null ? void 0 : n.id);
		It(t, void 0, a && i ? {
			questionId: a,
			questionRevision: i,
			clickedAtMs: Date.now(),
			prefetchRevision: i
		} : void 0);
	};
	g(() => {
		Bt && A === Ie && N("");
	}, [Bt, A]);
	let Ht = (e, t) => T((n) => ({
		...n,
		captureState: e,
		interviews: n.interviews.map((e) => e.id === C ? {
			...e,
			status: t
		} : e)
	})), Ut = async (t) => {
		if (!(Ze || H === "replaced")) {
			Qe(t), N("");
			try {
				let n = await l((n) => e.controlInterviewCapture(C, t, n));
				Ht(n, n === "paused" ? "paused" : "active");
			} catch (e) {
				N(e instanceof Error ? e.message : t === "pause" ? "暂停收音失败，请稍后重试。" : "恢复收音失败，请稍后重试。");
			} finally {
				Qe(null);
			}
		}
	}, Wt = async () => {
		if (!rt) {
			it(!0);
			try {
				nt(await l((t) => e.continueInterviewSession(C, t)));
			} finally {
				it(!1);
			}
		}
	}, Gt = async () => {
		if (window.confirm(Z ? "确认结束本场笔试？结束后仍可查看本场答题记录。" : "确认结束本场面试？结束后将停止采集并进入复盘。")) {
			try {
				await l((t) => e.endInterviewSession(C, t));
			} catch (e) {
				N(e instanceof Error ? e.message : Z ? "结束笔试失败，请稍后重试。" : "结束面试失败，请稍后重试。");
				return;
			}
			Ot(), Ht("ready", "ended"), se(a.review(C));
		}
	}, Kt = (e, t) => {
		if (t === "generating" && Ge.current.has(e)) {
			I("本次截图已提交，请重新截屏后再回答。");
			return;
		}
		let n = w.questions.find((t) => t.id === e);
		if (n) {
			if ((n.status === "cancelled" || n.status === "failed") && t === "generating") {
				if (n.input === "manual" || n.input === "desktop-audio") {
					It(n.text, e);
					return;
				}
				let r = `retry:${e}:${Date.now()}`, i = {
					id: `answer:${e}:${Date.now()}`,
					interviewId: C,
					userId: w.account.id,
					billingUsageId: r,
					questionId: e,
					question: n.text,
					revision: 1,
					status: "generating",
					partialText: "正在重新整理回答…",
					updatedAtMs: Date.now()
				};
				T((n) => ({
					...n,
					questions: n.questions.map((n) => n.id === e ? {
						...n,
						status: t
					} : n),
					activeAnswerTask: i
				}));
				return;
			}
			T((n) => ({
				...n,
				questions: n.questions.map((n) => n.id === e ? {
					...n,
					status: t
				} : n)
			}));
		}
	}, qt = (e) => {
		V.current || H === "replaced" || (Ot(), He.current = e, _e(e));
	}, Jt = async () => {
		if (!Z || !He.current || H === "replaced" || z.current || V.current || Q && ![
			"completed",
			"failed",
			"cancelled"
		].includes(Q.stage) || !ke || R.current.length >= ke) return;
		if (!e.captureScreenshot) {
			I("多屏截屏暂不可用，请刷新后重试。");
			return;
		}
		let t = new AbortController(), n = B.current;
		z.current = t, Ce(!0), I("");
		try {
			let r = await l((r) => e.captureScreenshot({ interviewId: C }, r, (e) => {
				t.signal.aborted || B.current !== n || I(e.stage === "waiting-desktop" ? "等待本地助手截屏…" : e.stage === "uploading" ? "正在上传截图…" : "正在截取当前画面…");
			}), t.signal);
			if (t.signal.aborted || B.current !== n || !He.current) {
				Dt([r]);
				return;
			}
			let i = [...R.current, r];
			R.current = i, ye(i), I("");
		} catch (e) {
			!t.signal.aborted && B.current === n && I(e instanceof Error ? e.message : "截屏失败，请重试。");
		} finally {
			z.current === t && (z.current = null, Ce(!1));
		}
	}, Yt = (e) => {
		if (z.current || V.current) return;
		let t = R.current.filter((t) => t.requestId === e), n = R.current.filter((t) => t.requestId !== e);
		R.current = n, ye(n), I(""), Dt(t);
	}, Xt = async () => {
		if (!Z || !He.current || H === "replaced" || z.current || V.current || R.current.length === 0 || Q && ![
			"completed",
			"failed",
			"cancelled"
		].includes(Q.stage)) return;
		if (!e.submitScreenshotBatch) {
			I("多屏回答暂不可用，请刷新后重试。");
			return;
		}
		let t = R.current, n = new AbortController(), r = B.current;
		V.current = !0, Ue.current = t, We.current = null, R.current = [], ye([]), L(!0), I(""), N(""), W.current = n, $({
			name: `${t.length} 张截图`,
			stage: "recognizing"
		});
		let i = `shot-batch-pending-${Date.now()}`;
		Ge.current.add(i);
		let a = {
			...Fe,
			id: i,
			text: `请根据 ${t.length} 张截图一起回答`,
			input: "screenshot",
			askedAt: "刚刚",
			status: "generating",
			advice: {
				...Fe.advice,
				detail: "正在识别多张截图并生成回答…",
				uncertain: !1
			}
		}, o = Nt(a, `screenshot:remote:batch:${Date.now()}`);
		T((e) => ({
			...e,
			questions: [a, ...e.questions],
			activeAnswerTask: o
		})), D((e) => ({
			...e,
			viewingAnswerId: null,
			newAnswerAvailable: !1
		}));
		let s = (e) => {
			n.signal.aborted || B.current !== r || (We.current = e.task, Ge.current.add(e.question.id), T((t) => {
				var n;
				return {
					...t,
					...F({
						questions: t.questions.filter((e) => e.id !== i),
						activeAnswerTask: ((n = t.activeAnswerTask) == null ? void 0 : n.questionId) === i ? null : t.activeAnswerTask
					}, {
						questions: [e.question],
						activeAnswerTask: e.task
					}, { preferIncomingTask: !0 })
				};
			}));
		};
		try {
			let i = await l((i) => e.submitScreenshotBatch({
				interviewId: C,
				captureRequestIds: t.map((e) => e.requestId),
				instruction: Zt
			}, i, (e) => {
				!n.signal.aborted && B.current === r && $(e);
			}, s), n.signal);
			if (n.signal.aborted || B.current !== r) return;
			s(i), k((e) => ({
				...e,
				screenshotTask: null,
				screenshotAnswerStatus: "success"
			})), i.task.status === "completed" && Mt();
		} catch (e) {
			var c;
			if (n.signal.aborted || B.current !== r) return;
			let t = `${e instanceof Error ? e.message : "多屏回答失败。"} 请重新截屏后再回答。`;
			I(t), $(null);
			let a = ((c = We.current) == null ? void 0 : c.questionId) ?? i;
			T((e) => ({
				...e,
				questions: e.questions.map((e) => e.id === a ? {
					...e,
					status: "failed",
					advice: {
						...e.advice,
						detail: t,
						uncertain: !0
					}
				} : e),
				activeAnswerTask: e.activeAnswerTask && e.activeAnswerTask.questionId === a ? {
					...e.activeAnswerTask,
					status: "failed",
					partialText: t
				} : e.activeAnswerTask
			})), k((e) => ({
				...e,
				screenshotAnswerStatus: "failed"
			}));
		} finally {
			Dt(t), B.current === r && (V.current = !1, Ue.current = [], We.current = null, L(!1)), W.current === n && (W.current = null);
		}
	}, Zt = "请只依据当前截图识别其中的题目、代码或系统设计内容，并给出可直接使用的中文回答。不要使用实时对话、面试官最近的问题或其他会话信息。", Qt = async () => {
		let t = `screenshot:remote:${Date.now()}`, n = `shot-pending-${Date.now()}`, r = {
			...Et,
			id: n,
			text: "请根据当前截图直接回答",
			input: "screenshot",
			askedAt: "刚刚",
			status: "generating",
			advice: {
				outline: [],
				detail: "正在识别当前截图并生成回答…",
				sourceTypes: [],
				inference: "",
				uncertain: !1,
				provenance: {
					selectionRevision: 0,
					usedSources: []
				}
			}
		}, i = Nt(r, t);
		T((e) => ({
			...e,
			questions: [r, ...e.questions],
			activeAnswerTask: i
		})), D((e) => ({
			...e,
			viewingAnswerId: null,
			newAnswerAvailable: !1
		}));
		try {
			var a;
			let t = await l((t) => e.submitScreenshotAnswer({
				interviewId: C,
				instruction: Zt
			}, t, (e) => $(e), (e) => {
				T((t) => {
					var r;
					return {
						...t,
						...F({
							questions: t.questions.filter((e) => e.id !== n),
							activeAnswerTask: ((r = t.activeAnswerTask) == null ? void 0 : r.questionId) === n ? null : t.activeAnswerTask
						}, {
							questions: [e.question],
							activeAnswerTask: e.task
						}, { preferIncomingTask: !0 })
					};
				});
			}), (a = W.current) == null ? void 0 : a.signal);
			T((e) => {
				var r;
				return {
					...e,
					...F({
						questions: e.questions.filter((e) => e.id !== n),
						activeAnswerTask: ((r = e.activeAnswerTask) == null ? void 0 : r.questionId) === n ? null : e.activeAnswerTask
					}, {
						questions: [t.question],
						activeAnswerTask: t.task
					}, { preferIncomingTask: !0 })
				};
			}), k((e) => ({
				...e,
				screenshotTask: null,
				screenshotAnswerStatus: "success"
			})), t.task.status === "completed" && Mt();
		} catch (e) {
			if (e instanceof DOMException && e.name === "AbortError" || e instanceof Error && e.message === "请求已取消") return;
			let t = e instanceof Error ? e.message : "截屏回答失败，请稍后重试。";
			T((e) => {
				var r;
				return {
					...e,
					questions: e.questions.map((e) => e.id === n ? {
						...e,
						status: "failed",
						advice: {
							...e.advice,
							detail: t,
							uncertain: !0
						}
					} : e),
					activeAnswerTask: ((r = e.activeAnswerTask) == null ? void 0 : r.questionId) === n ? {
						...e.activeAnswerTask,
						status: "failed",
						partialText: t,
						updatedAtMs: Date.now()
					} : e.activeAnswerTask
				};
			}), $t(t, "共享屏幕截取");
		}
	}, $t = (e, t = (Q == null ? void 0 : Q.name) ?? "当前屏幕截取") => {
		$({
			name: t,
			stage: "failed",
			errorMessage: e
		});
	}, en = (e) => e.stage === "failed" ? "截屏回答失败" : e.stage === "waiting-desktop" ? "等待本地助手" : e.stage === "uploading" ? "正在上传截图" : e.stage === "uploaded" ? "截图已上传" : e.stage === "recognizing" ? "正在识别截图" : e.stage === "generating" ? "正在生成答案" : e.stage === "completed" ? "截屏回答已完成" : e.stage === "cancelled" ? "截屏回答已取消" : "正在截取当前屏幕", tn = (e) => e.stage === "failed" ? e.errorMessage || "截屏回答失败，请稍后重试。" : e.stage === "waiting-desktop" ? "网页端已创建截屏任务，正在等待本地助手接收。" : e.stage === "uploading" ? "本地助手已接收任务，正在截取并上传压缩后的全屏截图。" : e.stage === "uploaded" ? "截图已上传到后端，正在准备交给视觉模型识别。" : e.stage === "recognizing" ? "正在识别截图中的题目、代码或系统设计内容。" : e.stage === "generating" ? null : e.stage === "completed" ? "截图回答已完成，答案会显示在右侧回答区。" : e.stage === "cancelled" ? "本次截屏回答已取消。" : "正在截取你选择的共享屏幕，不会跳转到上传页面。", nn = (e) => e instanceof DOMException && e.name === "AbortError" ? "" : e instanceof DOMException && e.name === "NotAllowedError" ? "共享屏幕截取未获授权，请检查电脑伴随程序权限后重试。" : e instanceof Error && e.message ? e.message : "共享屏幕暂时无法截取，请重试。", rn = async () => {
		var t;
		if (V.current) {
			let e = We.current;
			e && (q.current.add(e.id), q.current.add(e.questionId)), Ot(), k((e) => ({
				...e,
				screenshotTask: null,
				screenshotAnswerStatus: "cancelled"
			})), T((e) => ({
				...e,
				activeAnswerTask: e.activeAnswerTask ? {
					...e.activeAnswerTask,
					status: "cancelled",
					revision: e.activeAnswerTask.revision + 1
				} : null,
				questions: e.questions.map((t) => {
					var n;
					return t.id === ((n = e.activeAnswerTask) == null ? void 0 : n.questionId) ? {
						...t,
						status: "cancelled"
					} : t;
				})
			}));
			return;
		}
		let n = J.current;
		if (n) {
			bt.current.add(n), J.current = null, k((e) => ({
				...e,
				screenshotTask: null,
				screenshotAnswerStatus: "cancelled"
			}));
			try {
				await l((t) => e.cancelDesktopShortcutScreenshot(n, t));
			} catch (e) {
				bt.current.delete(n), $t(e instanceof Error ? e.message : "取消截屏回答失败，请稍后重试。");
			}
			return;
		}
		(t = W.current) == null || t.abort(), W.current = null, k((e) => ({
			...e,
			screenshotTask: null,
			screenshotAnswerStatus: "cancelled"
		})), T((e) => {
			let t = e.activeAnswerTask;
			return !t || !t.billingUsageId.startsWith("screenshot:remote:") || t.status !== "queued" && t.status !== "generating" ? e : {
				...e,
				activeAnswerTask: {
					...t,
					status: "cancelled",
					revision: t.revision + 1,
					updatedAtMs: Date.now()
				},
				questions: e.questions.map((e) => e.id === t.questionId ? {
					...e,
					status: "cancelled"
				} : e)
			};
		});
	}, an = () => {
		var e;
		if (Q && Q.stage !== "failed" && Q.stage !== "completed" && Q.stage !== "cancelled") {
			$({ ...Q });
			return;
		}
		N(""), (e = W.current) == null || e.abort();
		let t = new AbortController();
		W.current = t, $({
			name: "共享屏幕截取",
			stage: "capturing"
		}), window.setTimeout(() => {
			Promise.resolve().then(() => {
				if (!t.signal.aborted) return $({
					name: "共享屏幕截取",
					stage: "recognizing"
				}), Qt();
			}).then(() => {
				W.current = null;
			}).catch((e) => {
				if (t.signal.aborted || e instanceof DOMException && e.name === "AbortError") {
					W.current = null;
					return;
				}
				W.current = null, $t(nn(e));
			});
		}, 0);
	};
	yt.current = Z && P ? () => void Jt() : an, g(() => {
		let e = (e) => {
			H === "replaced" || e.repeat || e.altKey || e.metaKey || !e.ctrlKey || !e.shiftKey || e.code !== "Space" || (e.preventDefault(), e.stopPropagation(), yt.current());
		};
		return window.addEventListener("keydown", e, { capture: !0 }), () => window.removeEventListener("keydown", e, { capture: !0 });
	}, [H]);
	let on = () => T((e) => ({
		...e,
		speaker: {
			...e.speaker,
			pendingQuestion: null
		}
	})), sn = () => {
		w.speaker.pendingQuestion && T((e) => ({
			...e,
			speaker: {
				...e.speaker,
				pendingQuestion: null
			}
		}));
	}, cn = async () => {
		var t;
		let n = w.activeAnswerTask;
		if (!n || n.status !== "queued" && n.status !== "generating" || Ke) return;
		if (V.current) {
			await rn();
			return;
		}
		let r = (e, t, n) => T((r) => r.billing.activePass ? r : {
			...r,
			billing: {
				...r.billing,
				balance: r.billing.balance + t,
				ledger: [{
					id: `release-${e}`,
					userId: r.account.id,
					kind: "usage_release",
					points: t,
					createdAtMs: Date.now(),
					referenceId: e,
					description: n
				}, ...r.billing.ledger]
			}
		}), i = (e) => {
			var t;
			let i = (t = w.questions.find((e) => e.id === n.questionId)) == null ? void 0 : t.input;
			k((e) => ({
				...e,
				screenshotTask: i === "screenshot" ? null : e.screenshotTask,
				...i === "screenshot" ? { screenshotAnswerStatus: "cancelled" } : {},
				...i === "manual" ? {
					quickAnswerStatus: "cancelled",
					quickAnswerMessage: ""
				} : {}
			})), T((e) => ({
				...e,
				activeAnswerTask: {
					...n,
					status: "cancelled",
					revision: n.revision + 1,
					updatedAtMs: Date.now()
				},
				questions: e.questions.map((e) => e.id === n.questionId ? {
					...e,
					status: "cancelled"
				} : e)
			})), e && r(e.usageId, e.points, e.text);
		};
		if (n.billingUsageId.startsWith("pending:")) {
			var a;
			(a = G.current) == null || a.abort(), i();
			return;
		}
		if (n.billingUsageId.startsWith("screenshot:remote:")) {
			var o;
			(o = W.current) == null || o.abort(), W.current = null, i({
				usageId: n.billingUsageId,
				points: w.billing.rates.screenshotAnswerPoints,
				text: "截图回答已终止，积分预留已释放"
			});
			return;
		}
		(t = G.current) == null || t.abort(), qe(!0), Ye("");
		try {
			let t = await l((t) => e.cancelAnswer({
				interviewId: C,
				answerTaskId: n.id,
				expectedRevision: n.revision,
				idempotencyKey: `cancel:${n.id}:${n.revision}`
			}, n, t));
			if (t.outcome === "cancelled" || t.outcome === "already-cancelled") {
				var s;
				let e = (s = w.questions.find((e) => e.id === t.task.questionId)) == null ? void 0 : s.input;
				e === "manual" && k((e) => ({
					...e,
					quickAnswerStatus: "cancelled",
					quickAnswerMessage: ""
				})), e === "screenshot" && k((e) => ({
					...e,
					screenshotTask: null,
					screenshotAnswerStatus: "cancelled"
				})), T((e) => {
					let n = !t.task.billingUsageId.startsWith("live-answer:") && !t.task.billingUsageId.startsWith("pending:");
					return {
						...e,
						activeAnswerTask: t.task,
						questions: e.questions.map((e) => e.id === t.task.questionId ? {
							...e,
							status: "cancelled"
						} : e),
						billing: t.billingReleased && n && !e.billing.activePass ? {
							...e.billing,
							balance: e.billing.balance + e.billing.rates.answerPoints,
							ledger: [{
								id: `release-${t.task.billingUsageId}`,
								userId: e.account.id,
								kind: "usage_release",
								points: e.billing.rates.answerPoints,
								createdAtMs: Date.now(),
								referenceId: t.task.billingUsageId,
								description: "回答已终止，积分预留已释放"
							}, ...e.billing.ledger]
						} : e.billing
					};
				});
			} else Ye(t.outcome === "stale-revision" ? "回答状态刚刚发生变化，请重试。" : "回答已经完成，无法终止。");
		} catch {
			Ye("终止回答失败，当前回答状态未改变，请重试。");
		} finally {
			qe(!1);
		}
	}, ln = () => {
		var e;
		(e = W.current) == null || e.abort(), W.current = null, $(null), T((e) => {
			let t = e.activeAnswerTask;
			return !t || t.status !== "failed" || !t.billingUsageId.startsWith("screenshot:remote:") ? e : {
				...e,
				activeAnswerTask: null
			};
		});
	}, un = A.includes("积分") || A.includes("会员") || A.toLowerCase().includes("billing"), dn = A === Ie, fn = w.captureState === "capturing" || w.captureState === "reconnecting", pn = H === "replaced" ? "已在其他页面继续" : fn ? "正在收音" : w.captureState === "paused" ? "收音已暂停" : w.captureState === "permission-required" ? "采集能力不可用" : w.captureState === "error" ? "设备连接异常" : "已连接，未采集", mn = fn ? /* @__PURE__ */ j("button", {
		className: "button warning live-session-control",
		disabled: H === "replaced" || Ze !== null,
		onClick: () => void Ut("pause"),
		children: Ze === "pause" ? "暂停中…" : "暂停收音"
	}) : /* @__PURE__ */ j("button", {
		className: "button primary live-session-control",
		disabled: H === "replaced" || Ze !== null || w.captureState !== "ready" && w.captureState !== "paused",
		onClick: () => w.captureState === "paused" ? void Ut("resume") : Ht("capturing", "active"),
		children: Ze === "resume" ? "恢复中…" : w.captureState === "paused" ? "恢复收音" : "开始面试"
	}), hn = (e) => {
		k((t) => ({
			...t,
			manualDraft: e,
			quickAnswerStatus: "idle",
			quickAnswerMessage: ""
		})), e.trim() && A === Ie && N("");
	}, gn = /* @__PURE__ */ j(u, {
		state: w,
		interviewAudioMode: (X == null ? void 0 : X.interviewAudioMode) ?? "computer",
		onConfirmQuestion: H === "replaced" ? on : sn,
		onDismissQuestion: on
	}), _n = /* @__PURE__ */ j(t, {
		answers: w.questions,
		cancelledWebAnswerIds: ht.current,
		viewingAnswerId: E.viewingAnswerId,
		newAnswerAvailable: E.newAnswerAvailable,
		activeTask: w.activeAnswerTask,
		cancelling: Ke,
		cancelError: Je,
		interviewLanguage: (X == null ? void 0 : X.interviewLanguage) ?? "zh-CN",
		onStop: () => void cn(),
		onView: (e) => D((t) => ({
			...t,
			viewingAnswerId: e,
			newAnswerAvailable: e ? t.newAnswerAvailable : !1
		})),
		onRetry: Kt
	});
	return Z ? /* @__PURE__ */ M("main", {
		className: `live-page focused-live-page${U ? " desktop-live-page" : " mobile-live-page"}`,
		children: [
			/* @__PURE__ */ M("header", {
				className: "live-top",
				children: [
					/* @__PURE__ */ j(n, {
						to: a.writtenExams,
						"aria-label": "返回笔试模式",
						children: s
					}),
					/* @__PURE__ */ M("div", {
						className: "live-session-heading",
						children: [
							/* @__PURE__ */ j("strong", { children: wt }),
							/* @__PURE__ */ M("span", { children: [/* @__PURE__ */ j("i", { className: "online-dot" }), " 桌面助手已连接 · 截屏回答可用"] }),
							/* @__PURE__ */ j("small", {
								className: "live-language-badge",
								children: "笔试模式"
							})
						]
					}),
					/* @__PURE__ */ M("div", {
						className: "live-top-actions",
						children: [
							/* @__PURE__ */ M("div", {
								className: "live-auto-answer",
								children: [/* @__PURE__ */ j("span", { children: "多屏回答" }), /* @__PURE__ */ M("label", {
									className: "switch-control",
									children: [/* @__PURE__ */ j("input", {
										type: "checkbox",
										role: "switch",
										"aria-label": "多屏回答",
										checked: P,
										disabled: Oe || !be && O.screenshotAnswerStatus === "processing" || H === "replaced",
										onChange: (e) => qt(e.target.checked)
									}), /* @__PURE__ */ j("span", { "aria-hidden": "true" })]
								})]
							}),
							/* @__PURE__ */ j(n, {
								className: "live-balance",
								to: a.billing,
								children: "积分与会员"
							}),
							c,
							/* @__PURE__ */ j("button", {
								className: "button danger live-session-control",
								disabled: H === "replaced",
								onClick: () => void Gt(),
								children: "结束笔试"
							})
						]
					})
				]
			}),
			A ? /* @__PURE__ */ M("div", {
				className: "global-live-alert",
				role: "alert",
				children: [/* @__PURE__ */ j("strong", { children: A }), /* @__PURE__ */ j("button", {
					type: "button",
					onClick: () => N(""),
					children: "关闭"
				})]
			}) : null,
			H === "replaced" ? /* @__PURE__ */ M("div", {
				className: "global-live-alert replaced-page-alert",
				role: "status",
				children: [/* @__PURE__ */ j("strong", { children: "本场笔试已在其他页面继续" }), /* @__PURE__ */ j(n, {
					className: "button primary",
					to: a.writtenExams,
					children: "返回笔试模式"
				})]
			}) : null,
			/* @__PURE__ */ j("div", {
				className: "written-exam-workspace",
				children: /* @__PURE__ */ M("section", {
					className: "answer-column",
					children: [_n, /* @__PURE__ */ j(le, {
						manualDraft: "",
						screenshotTask: O.screenshotTask,
						screenshotOnly: !0,
						screenshotAnswerStatus: O.screenshotAnswerStatus ?? "idle",
						disabled: H === "replaced" || Oe,
						onQuickAnswer: () => void 0,
						onScreenshot: P ? () => void Jt() : an,
						multiScreen: P,
						pendingScreenshots: ve,
						screenshotLimit: ke ?? 4,
						captureBusy: be,
						captureUnavailable: ke === null,
						captureMessage: De || Be || (ke === null ? "正在读取截屏设置…" : ""),
						onBatchAnswer: () => void Xt(),
						onRemoveScreenshot: Yt
					})]
				})
			}),
			Q && H !== "replaced" ? /* @__PURE__ */ j("div", {
				className: "sheet-backdrop",
				role: "dialog",
				"aria-modal": "true",
				"aria-labelledby": "screenshot-dialog-title",
				children: /* @__PURE__ */ M("section", {
					className: "sheet",
					children: [
						/* @__PURE__ */ j("h2", {
							id: "screenshot-dialog-title",
							children: en(Q)
						}),
						tn(Q) ? /* @__PURE__ */ j("p", { children: tn(Q) }) : null,
						Q.stage === "failed" ? /* @__PURE__ */ M("div", {
							className: "sheet-actions split-actions",
							children: [/* @__PURE__ */ j("button", {
								className: "button ghost full",
								onClick: ln,
								children: "删除本次失败"
							}), /* @__PURE__ */ j("button", {
								className: "button primary full",
								onClick: an,
								children: "重新截屏"
							})]
						}) : /* @__PURE__ */ j("button", {
							className: "button primary full",
							onClick: () => void rn(),
							children: "取消"
						})
					]
				})
			}) : null,
			/* @__PURE__ */ M("footer", {
				className: "session-bar",
				children: [/* @__PURE__ */ M("div", { children: [/* @__PURE__ */ j("i", { className: "online-dot" }), /* @__PURE__ */ j("strong", { children: "笔试进行中" })] }), /* @__PURE__ */ j("div", { children: /* @__PURE__ */ j("small", { children: "仅在你主动发起时截屏并生成回答" }) })]
			})
		]
	}) : /* @__PURE__ */ M("main", {
		className: `live-page focused-live-page${U ? " desktop-live-page" : " mobile-live-page"}`,
		children: [
			/* @__PURE__ */ M("header", {
				className: "live-top",
				children: [
					/* @__PURE__ */ j(n, {
						to: a.app,
						"aria-label": "返回面试首页",
						children: s
					}),
					/* @__PURE__ */ M("div", {
						className: "live-session-heading",
						children: [
							/* @__PURE__ */ j("strong", { children: wt }),
							/* @__PURE__ */ M("span", { children: [
								/* @__PURE__ */ j("i", { className: fn ? "recording-dot" : "online-dot" }),
								" ",
								U ? `这台设备 · ${pn}` : pn
							] }),
							/* @__PURE__ */ j("small", {
								className: "live-language-badge",
								children: Tt
							})
						]
					}),
					U ? /* @__PURE__ */ M("div", {
						className: "live-top-actions",
						children: [
							/* @__PURE__ */ M("div", {
								className: "live-auto-answer",
								children: [/* @__PURE__ */ j("span", { children: "自动回答" }), /* @__PURE__ */ M("label", {
									className: "switch-control",
									children: [/* @__PURE__ */ j("input", {
										type: "checkbox",
										role: "switch",
										"aria-label": "自动回答",
										checked: (X == null ? void 0 : X.autoAnswerEnabled) ?? !1,
										disabled: at || H === "replaced",
										onChange: (e) => void Rt(e.target.checked)
									}), /* @__PURE__ */ j("span", { "aria-hidden": "true" })]
								})]
							}),
							/* @__PURE__ */ j(m, {
								enabled: O.webSearchEnabled === !0,
								disabled: H === "replaced",
								onToggle: Lt
							}),
							/* @__PURE__ */ j(n, {
								className: "live-balance",
								to: a.billing,
								children: "积分与会员"
							}),
							/* @__PURE__ */ M("details", {
								className: "live-contact-menu",
								children: [/* @__PURE__ */ j("summary", { children: "联系我们" }), /* @__PURE__ */ j("div", {
									className: "live-contact-popover",
									"aria-label": "官方社交账号",
									children: Ne.map((e) => /* @__PURE__ */ M("p", { children: [/* @__PURE__ */ j("small", { children: e.label }), /* @__PURE__ */ j("strong", { children: e.account })] }, e.id))
								})]
							}),
							/* @__PURE__ */ j("span", { children: "18:24" }),
							c,
							mn,
							/* @__PURE__ */ j("button", {
								className: "button danger live-session-control",
								disabled: H === "replaced",
								onClick: () => void Gt(),
								children: "结束面试"
							})
						]
					}) : /* @__PURE__ */ M("div", {
						className: "mobile-live-top-actions",
						children: [
							/* @__PURE__ */ M("div", {
								className: "live-auto-answer mobile",
								children: [/* @__PURE__ */ j("span", { children: "自动" }), /* @__PURE__ */ M("label", {
									className: "switch-control",
									children: [/* @__PURE__ */ j("input", {
										type: "checkbox",
										role: "switch",
										"aria-label": "自动回答",
										checked: (X == null ? void 0 : X.autoAnswerEnabled) ?? !1,
										disabled: at || H === "replaced",
										onChange: (e) => void Rt(e.target.checked)
									}), /* @__PURE__ */ j("span", { "aria-hidden": "true" })]
								})]
							}),
							/* @__PURE__ */ j(m, {
								mobile: !0,
								enabled: O.webSearchEnabled === !0,
								disabled: H === "replaced",
								onToggle: Lt
							}),
							mn,
							/* @__PURE__ */ M("details", {
								className: "mobile-live-more",
								children: [/* @__PURE__ */ j("summary", {
									"aria-label": "更多面试操作",
									children: "•••"
								}), /* @__PURE__ */ M("div", { children: [
									/* @__PURE__ */ j(n, {
										to: a.billing,
										children: "积分与会员"
									}),
									/* @__PURE__ */ j(n, {
										to: a.settings,
										children: "用户设置"
									}),
									/* @__PURE__ */ j("section", {
										className: "mobile-live-contact-list",
										"aria-label": "官方社交账号",
										children: Ne.map((e) => /* @__PURE__ */ M("p", { children: [/* @__PURE__ */ j("small", { children: e.label }), /* @__PURE__ */ j("strong", { children: e.account })] }, e.id))
									}),
									/* @__PURE__ */ j("button", {
										className: "danger",
										disabled: H === "replaced",
										onClick: () => void Gt(),
										children: "结束面试"
									})
								] })]
							})
						]
					})
				]
			}),
			(tt == null ? void 0 : tt.state) === "warning" ? /* @__PURE__ */ M("div", {
				className: "global-live-alert",
				role: "status",
				children: [
					/* @__PURE__ */ j("strong", { children: "本场面试即将因空闲自动结束" }),
					/* @__PURE__ */ j("span", { children: "连续 20 分钟没有音频、回答或截图活动会释放当前设备连接，历史记录仍会保留。" }),
					/* @__PURE__ */ j("button", {
						className: "button primary",
						disabled: rt,
						onClick: () => void Wt(),
						children: rt ? "正在继续…" : "继续本场面试"
					})
				]
			}) : null,
			H === "replaced" ? /* @__PURE__ */ M("div", {
				className: "global-live-alert replaced-page-alert",
				role: "status",
				children: [
					/* @__PURE__ */ j("strong", { children: "本场面试已在其他页面继续" }),
					/* @__PURE__ */ j("span", { children: "当前页面已停止收音同步、实时订阅和回答请求；已显示内容仍可查看。关闭此页或返回面试首页即可。" }),
					/* @__PURE__ */ j(n, {
						className: "button primary",
						to: a.app,
						children: "返回面试首页"
					})
				]
			}) : null,
			w.captureState === "permission-required" || w.captureState === "error" ? /* @__PURE__ */ M("div", {
				className: "global-live-alert",
				role: "status",
				children: [
					/* @__PURE__ */ j("strong", { children: w.captureState === "permission-required" ? "助手采集能力不可用" : "桌面设备连接异常" }),
					/* @__PURE__ */ j("span", { children: w.captureState === "permission-required" ? "请在桌面助手中检查首次授权状态；网页不会申请麦克风或屏幕权限，手动输入仍可使用。" : "可以运行诊断，当前仍可使用手动问题和截图。" }),
					/* @__PURE__ */ j("button", {
						onClick: () => w.captureState === "permission-required" ? Ht("ready", "ready") : et((e) => e + 1),
						children: w.captureState === "permission-required" ? "关闭提示" : "重新诊断"
					})
				]
			}) : null,
			A ? /* @__PURE__ */ M("div", {
				className: "global-live-alert",
				role: "status",
				children: [
					/* @__PURE__ */ j("strong", { children: A }),
					/* @__PURE__ */ j("span", { children: dn ? "请等待面试官问题识别完成，或在左侧手动输入问题后再使用快答。" : un ? "当前任务未启动，请检查积分或会员权益。" : "当前回答没有成功启动，请根据上方原因重试。" }),
					un ? /* @__PURE__ */ j(n, {
						className: "button primary",
						to: a.billing,
						children: "前往积分与会员"
					}) : null
				]
			}) : null,
			U ? /* @__PURE__ */ M("div", {
				ref: dt,
				className: `live-grid focused-live-grid${H === "replaced" ? " live-grid-readonly" : ""}`,
				style: { gridTemplateColumns: `minmax(240px, ${E.splitRatio}fr) 12px minmax(300px, ${100 - E.splitRatio}fr)` },
				children: [
					/* @__PURE__ */ M("section", {
						className: "conversation-column",
						children: [gn, /* @__PURE__ */ j(d, {
							manualDraft: O.manualDraft,
							disabled: H === "replaced",
							onChange: hn
						})]
					}),
					/* @__PURE__ */ j(h, {
						containerRef: dt,
						ratio: E.splitRatio,
						bounds: st,
						onChange: (e) => D((t) => ({
							...t,
							splitRatio: e
						}))
					}),
					/* @__PURE__ */ M("section", {
						className: "answer-column",
						children: [_n, /* @__PURE__ */ j(le, {
							manualDraft: O.manualDraft,
							latestInterviewerQuestion: Bt,
							screenshotTask: O.screenshotTask,
							quickAnswerStatus: O.quickAnswerStatus ?? "idle",
							quickAnswerMessage: O.quickAnswerMessage ?? "",
							screenshotAnswerStatus: O.screenshotAnswerStatus ?? "idle",
							disabled: H === "replaced",
							onQuickAnswer: Vt,
							onScreenshot: an
						})]
					})
				]
			}) : /* @__PURE__ */ M("div", {
				className: `mobile-live-workspace${H === "replaced" ? " live-grid-readonly" : ""}`,
				children: [
					/* @__PURE__ */ M("nav", {
						className: "mobile-live-tabs",
						role: "tablist",
						"aria-label": "面试内容",
						children: [/* @__PURE__ */ M("button", {
							role: "tab",
							"aria-selected": lt === "answer",
							className: lt === "answer" ? "active" : "",
							onClick: () => ut("answer"),
							children: ["回答", w.activeAnswerTask && ["pending", "generating"].includes(w.activeAnswerTask.status) ? /* @__PURE__ */ j("span", { children: "生成中" }) : null]
						}), /* @__PURE__ */ M("button", {
							role: "tab",
							"aria-selected": lt === "conversation",
							className: lt === "conversation" ? "active" : "",
							onClick: () => ut("conversation"),
							children: ["对话", /* @__PURE__ */ j("span", { children: w.speaker.transcripts.length })]
						})]
					}),
					/* @__PURE__ */ j("section", {
						className: `mobile-live-panel ${lt}`,
						role: "tabpanel",
						children: lt === "answer" ? _n : gn
					}),
					/* @__PURE__ */ j(f, {
						manualDraft: O.manualDraft,
						latestInterviewerQuestion: Bt,
						screenshotTask: O.screenshotTask,
						quickAnswerStatus: O.quickAnswerStatus ?? "idle",
						quickAnswerMessage: O.quickAnswerMessage ?? "",
						screenshotAnswerStatus: O.screenshotAnswerStatus ?? "idle",
						disabled: H === "replaced",
						onChange: hn,
						onQuickAnswer: () => {
							ut("answer"), Vt();
						},
						onScreenshot: () => {
							ut("answer"), an();
						}
					})
				]
			}),
			Q && H !== "replaced" ? /* @__PURE__ */ j("div", {
				className: "sheet-backdrop",
				role: "dialog",
				"aria-modal": "true",
				"aria-labelledby": "screenshot-dialog-title",
				children: /* @__PURE__ */ M("section", {
					className: "sheet",
					children: [
						/* @__PURE__ */ j("h2", {
							id: "screenshot-dialog-title",
							children: en(Q)
						}),
						tn(Q) ? /* @__PURE__ */ j("p", { children: tn(Q) }) : null,
						Q.stage === "failed" ? /* @__PURE__ */ M("div", {
							className: "sheet-actions split-actions",
							children: [/* @__PURE__ */ j("button", {
								className: "button ghost full",
								onClick: ln,
								children: "删除本次失败"
							}), /* @__PURE__ */ j("button", {
								className: "button primary full",
								onClick: an,
								children: "重新截屏"
							})]
						}) : /* @__PURE__ */ j("button", {
							className: "button primary full",
							onClick: () => void rn(),
							children: "取消"
						})
					]
				})
			}) : null,
			U ? /* @__PURE__ */ M("footer", {
				className: "session-bar",
				children: [/* @__PURE__ */ M("div", { children: [/* @__PURE__ */ j("i", { className: fn ? "recording-dot" : "online-dot" }), /* @__PURE__ */ j("strong", { children: fn ? "面试进行中" : w.captureState === "paused" ? "面试已暂停" : "等待开始面试" })] }), /* @__PURE__ */ j("div", { children: /* @__PURE__ */ j("small", { children: fn ? "正在持续接收面试官与我的实时对话" : "开始面试后会在头部右侧管理本场状态" }) })]
			}) : null
		]
	});
}
//#endregion
//#region artifacts/cn-written-multi-screen-20261019-release/web/module-src/entry.tsx
function Be(e) {
	var t;
	let { id: n } = i(), { state: r } = o();
	return ((t = r.interviews.find((e) => e.id === n)) == null ? void 0 : t.sessionMode) === "written" ? /* @__PURE__ */ j(ze, { ...e }) : /* @__PURE__ */ j(p, { ...e });
}
//#endregion
export { Be as LivePage };
