import { n as e, t } from "./jsx-runtime-2Zwg-L3c.js";
import { F as n, L as r, R as i, S as a, b as o, x as s } from "./main-8b805158.js";
import { t as c } from "./auth-client-CpBLJDBI.js";
import { n as l, t as ee } from "./mock-interview-report-CtmMBUmT.js";
var { useCallback: te, useEffect: u, useState: d, useRef: f } = e();
//#endregion
//#region artifacts/cn-mock-flat-billing-20261015/web/module-src/mock-interview-client.ts
function ne(e) {
	let t = Date.parse(`${e.quotaDay}T00:00:00+08:00`) + 864e5 - e.nowMs;
	return Number.isFinite(t) ? Math.max(100, t + 100) : 6e4;
}
//#endregion
//#region artifacts/cn-mock-flat-billing-20261015/web/module-src/jsx-runtime.ts
var { jsx: p, jsxs: m, Fragment: h } = t(), g = {
	playing: !1,
	levels: Array(21).fill(0)
};
function re({ player: e, phase: t }) {
	let [n, r] = d(g), [i, a] = d(!1);
	u(() => {
		var e, t;
		let n = (e = (t = window).matchMedia) == null ? void 0 : e.call(t, "(prefers-reduced-motion: reduce)"), r = () => a((n == null ? void 0 : n.matches) ?? !1);
		return r(), n == null || n.addEventListener("change", r), () => n == null ? void 0 : n.removeEventListener("change", r);
	}, []), u(() => e.subscribePlayback((e) => {
		r(i ? (t) => t.playing === e.playing ? t : {
			...g,
			playing: e.playing
		} : e);
	}), [e, i]);
	let o = t === "speaking" && n.playing, s = o ? "面试官正在提问" : t === "speaking" ? "等待语音播放" : t === "paused" ? "语音播放已暂停" : t === "listening" ? "正在聆听你的回答" : "等待面试官提问";
	return /* @__PURE__ */ m("div", {
		className: `mock-playback ${o ? "is-active" : ""} ${i ? "is-reduced-motion" : ""}`,
		children: [/* @__PURE__ */ p("div", {
			className: "mock-waveform",
			"aria-hidden": "true",
			children: n.levels.map((e, t) => /* @__PURE__ */ p("span", { style: { transform: `scaleY(${o && !i ? .12 + e * .88 : .12})` } }, t))
		}), /* @__PURE__ */ m("span", {
			className: "mock-playback-label",
			role: "status",
			children: [/* @__PURE__ */ p("i", { "aria-hidden": "true" }), s]
		})]
	});
}
//#endregion
//#region artifacts/cn-mock-flat-billing-20261015/web/module-src/MockInterviewPage.tsx
var _ = {
	preparing: "面试准备",
	generating_question: "面试官正在出题",
	speaking: "听听面试官的问题",
	listening: "轮到你回答",
	paused: "已暂停",
	generating_report: "正在整理面试报告",
	completed: "本场练习已结束"
}, v = (e) => e instanceof Error ? e.message : "操作暂时不可用，请重试。";
function ie() {
	let { id: e } = i(), t = r(), [l, ee] = d([]), [g, ie] = d(null), [y, oe] = d(null), [b, se] = d([]), [x, ce] = d(""), [le, ue] = d(""), [S, de] = d(!1), [fe, pe] = d(null), [me, C] = d(""), [w, T] = d(!1), [E, D] = d(!1), O = f(void 0), k = f(!1), A = f(null), [j, M] = d(!1), [N, P] = d(""), [he, ge] = d(!1), [F, I] = d(""), [L, R] = d(!1), [z, _e] = d(null), [ve, B] = d(!1), V = f(null), H = f(null), U = f(!1), W = f(""), ye = f(""), G = f(new o()), K = f(null), be = f(0), xe = f(null), q = f(null), J = f(!1), [Se, Ce] = d(0), we = (e) => {
		var t, n;
		let r = H.current;
		(r == null || (t = r.state.rounds.at(-1)) == null ? void 0 : t.question_id) !== ((n = e.state.rounds.at(-1)) == null ? void 0 : n.question_id) && (P(""), U.current = !1, ge(!1), xe.current = null, W.current = "", ye.current = ""), e.state.capture_epoch && e.state.capture_epoch !== (r == null ? void 0 : r.state.capture_epoch) && (ye.current = W.current), e.state.phase !== "speaking" && (G.current.stop(), B(!1), q.current = null, A.current = null, T(!1), clearTimeout(O.current), D(!1)), H.current = e, oe(e);
	}, Y = (e, t = {}) => {
		var n, r;
		let i = H.current;
		if (!i || ((n = V.current) == null ? void 0 : n.readyState) !== WebSocket.OPEN) {
			I("连接已断开，请重新连接后操作。");
			return;
		}
		I(""), V.current.send(JSON.stringify({
			action: e,
			version: i.state.version,
			...[
				"listen",
				"replay",
				"speak",
				"playback_started",
				"playback_waiting",
				"submit"
			].includes(e) ? { questionId: (r = i.state.rounds.at(-1)) == null ? void 0 : r.question_id } : {},
			...t
		}));
	}, Te = (e) => {
		var t, n;
		((t = H.current) == null ? void 0 : t.state.phase) !== "speaking" || ((n = H.current.state.rounds.at(-1)) == null ? void 0 : n.question_id) !== e || (A.current = e, T(!k.current), k.current && (A.current = null, Y("listen")));
	}, Ee = (e) => {
		clearTimeout(O.current), A.current = null, D(!0), J.current && (J.current = !1, Y("playback_waiting")), O.current = setTimeout(() => {
			D(!1), Te(e);
		}, 1500);
	};
	G.current.onIdle = () => {
		var e;
		J.current && ((e = H.current) == null ? void 0 : e.state.phase) === "speaking" && (J.current = !1, Y("playback_waiting"));
	};
	let X = te(async () => {
		let e = ++be.current, t = await s("/mock-interviews");
		e === be.current && (ee(t.sessions), ie(t.quote));
	}, []);
	u(() => {
		if (e || z !== !0) return;
		let t = !1, n = () => {
			X().catch((e) => {
				t || I(v(e));
			});
		}, r = g ? setTimeout(n, ne(g)) : void 0, i = () => {
			document.visibilityState === "visible" && n();
		};
		return document.addEventListener("visibilitychange", i), () => {
			t = !0, clearTimeout(r), document.removeEventListener("visibilitychange", i);
		};
	}, [
		e,
		z,
		g,
		X
	]), u(() => {
		let t = !1;
		return s("/mock-interviews/capabilities").then(async (n) => {
			if (!t && (_e(n.enabled), n.enabled)) if (e) {
				let n = await s(`/mock-interviews/${encodeURIComponent(e)}`);
				if (t) return;
				if (we(n), n.state.phase === "preparing") {
					let e = await s("/documents?documentKind=resume");
					t || se(e.filter((e) => e.status === "ready" && e.indexState === "indexed" && e.documentVersionId));
				}
			} else await X();
		}).catch((e) => {
			t || I(v(e));
		}), () => {
			t = !0, be.current++, H.current = null, oe(null);
		};
	}, [e, X]);
	let De = !!(e && y && y.state.phase !== "completed");
	u(() => {
		if (!e || !De) return;
		let t = c.readStoredSession();
		if (!t) {
			I("请先重新登录。");
			return;
		}
		let n = !1, r, i = new WebSocket(a(e));
		return V.current = i, i.onopen = () => {
			i.send(JSON.stringify({ accessToken: t.accessToken })), r = setInterval(() => {
				i.readyState === WebSocket.OPEN && i.send(JSON.stringify({ action: "heartbeat" }));
			}, 5e3);
		}, i.onmessage = (e) => {
			if (!n) try {
				let a = JSON.parse(String(e.data));
				if (a.type === "state") {
					var t;
					let e = (t = H.current) == null ? void 0 : t.state.phase;
					if (k.current = (a.microphoneConnected ?? a.desktopConnected) === !0, pe(a.preparation ?? null), C(""), M(!0), de(a.desktopConnected === !0), we(a.session), A.current && k.current && Te(A.current), a.session.state.phase === "speaking" && e !== "speaking") {
						var r;
						G.current.stop(), J.current = !1, q.current = ((r = a.session.state.rounds.at(-1)) == null ? void 0 : r.question_id) ?? null, G.current.unlock().then(() => {
							n || Y("speak");
						}).catch((e) => I(v(e)));
					}
				} else if (a.type === "transcript") {
					var i;
					!U.current && a.epoch === ((i = H.current) == null ? void 0 : i.state.capture_epoch) && (W.current = [ye.current, String(a.text)].filter(Boolean).join(" ").slice(0, 8e3), P(W.current));
				} else a.type === "audio" && a.questionId === q.current ? (G.current.append(a.pcm), J.current || (J.current = !0, Y("playback_started")), B(!0)) : a.type === "audio_end" && a.questionId === q.current ? G.current.finish(() => {
					B(!1), n || Ee(a.questionId);
				}) : (a.type === "error" || a.type === "speech_unavailable") && (I(a.message), R(!1), a.type === "speech_unavailable" && (G.current.stop(), B(!1)));
			} catch (e) {
				G.current.stop(), B(!1), I(v(e)), Y("pause");
			}
		}, i.onclose = () => {
			clearInterval(r), clearTimeout(O.current), G.current.close(), D(!1), k.current = !1, A.current = null, T(!1), n || (M(!1), B(!1), I("面试连接已断开，收音已暂停。请重新连接；本场结束时间保持不变。"));
		}, () => {
			n = !0, clearInterval(r), clearTimeout(O.current), G.current.close(), i.close(), V.current = null, k.current = !1, A.current = null, M(!1);
		};
	}, [
		e,
		De,
		Se
	]);
	let Z = async (e) => {
		R(!0), I("");
		try {
			await e();
		} catch (e) {
			I(v(e));
		} finally {
			R(!1);
		}
	}, Oe = () => Z(async () => {
		var t;
		C("");
		let n = c.readStoredSession();
		if (!n) throw Error("请重新登录");
		await s(`/realtime-speech/sessions/${e}/desktop-binding`, {
			userId: n.account.id,
			manualCode: le
		}), C("机器码已绑定，正在检查助手状态…"), ((t = V.current) == null ? void 0 : t.readyState) === WebSocket.OPEN && V.current.send(JSON.stringify({ action: "heartbeat" }));
	}), ke = () => Z(async () => {
		if (!g || g.entryPoints && !window.confirm(`本场一次性扣 ${g.entryPoints} 积分，开始后 ${g.durationLimitMinutes} 分钟自动结束。确认创建？`)) return;
		K.current ??= crypto.randomUUID();
		let e;
		try {
			e = await s("/mock-interviews", {
				idempotencyKey: K.current,
				title: x.trim() ? `${x.trim()} · 模拟面试` : "模拟面试",
				targetRole: x,
				expectedBillingClass: g.billingClass
			});
		} catch (e) {
			try {
				await X();
			} catch {}
			throw e;
		}
		K.current = null, t(`/app/mock-interviews/${e.sessionId}`);
	});
	if (z === !1) return /* @__PURE__ */ m("main", {
		className: "app-page mock-page",
		children: [
			/* @__PURE__ */ p("h1", { children: "模拟面试尚未开放" }),
			/* @__PURE__ */ p("p", { children: "正式开放前，原有面试功能不受影响。" }),
			/* @__PURE__ */ p(n, {
				to: "/app",
				children: "返回面试模式"
			})
		]
	});
	if (!e) return /* @__PURE__ */ m("main", {
		className: "app-page mock-page",
		children: [
			/* @__PURE__ */ m("header", {
				className: "mock-page-heading",
				children: [/* @__PURE__ */ m("div", { children: [
					/* @__PURE__ */ p("span", {
						className: "eyebrow",
						children: "AI PRACTICE"
					}),
					/* @__PURE__ */ p("h1", { children: "把下一次面试，提前练一遍。" }),
					/* @__PURE__ */ p("p", { children: "围绕你的简历展开，最多 10 道问题。按自己的节奏回答，结束后获得反馈。" })
				] }), /* @__PURE__ */ m("span", {
					className: "mock-pill",
					children: [
						"已保存 ",
						(g == null ? void 0 : g.savedCount) ?? "—",
						" / 2"
					]
				})]
			}),
			F && /* @__PURE__ */ p("p", {
				role: "alert",
				className: "mock-alert",
				children: F
			}),
			/* @__PURE__ */ m("section", {
				className: "mock-create-grid",
				children: [/* @__PURE__ */ m("div", {
					className: "mock-portrait",
					children: [/* @__PURE__ */ p("img", {
						src: "/assets/mock-interview/interviewer-v1.png",
						alt: "原创虚拟 AI 面试官形象"
					}), /* @__PURE__ */ m("div", { children: [/* @__PURE__ */ p("span", {
						className: "mock-pill",
						children: "AI 模拟面试官"
					}), /* @__PURE__ */ p("h2", { children: "一次对话，一次更充分的准备。" })] })]
				}), /* @__PURE__ */ m("div", {
					className: "mock-panel",
					children: [
						/* @__PURE__ */ p("span", {
							className: "eyebrow",
							children: "开始练习"
						}),
						/* @__PURE__ */ p("h2", { children: "这次，想准备什么岗位？" }),
						/* @__PURE__ */ m("label", { children: [
							"目标岗位 ",
							/* @__PURE__ */ p("span", { children: "选填" }),
							/* @__PURE__ */ p("input", {
								value: x,
								maxLength: 80,
								disabled: L,
								onChange: (e) => {
									ce(e.target.value), K.current = null;
								},
								placeholder: "例如：后端开发工程师"
							})
						] }),
						/* @__PURE__ */ m("div", {
							className: "mock-price",
							children: [/* @__PURE__ */ p("strong", { children: (g == null ? void 0 : g.entryPoints) === 0 ? "本场免费" : "100 积分 / 场" }), /* @__PURE__ */ p("p", { children: (g == null ? void 0 : g.entryPoints) === 0 ? `有效会员今日剩余 ${g.dailyFreeRemaining} 场免费模拟面试。` : "每场一次性扣 100 积分，朗读、回答和报告不额外收费。" })]
						}),
						/* @__PURE__ */ m("ul", {
							className: "mock-notes",
							children: [
								/* @__PURE__ */ p("li", { children: "创建后选择一份已解析简历，连接现有正式版桌面助手，无需为此升级助手。" }),
								/* @__PURE__ */ m("li", { children: [
									"所有有效会员每天免费 ",
									(g == null ? void 0 : g.dailyFreeLimit) ?? 1,
									" 场，北京时间 00:00 更新；当天免费次数用完后，100 积分 / 场。"
								] }),
								/* @__PURE__ */ m("li", { children: [
									"开始后 ",
									(g == null ? void 0 : g.durationLimitMinutes) ?? 60,
									" 分钟自动结束；准备阶段不计时，暂停、出题等待和断线不延长结束时间。"
								] }),
								/* @__PURE__ */ p("li", { children: "结束自动保存问答和报告，最多 2 场；不保存原始音频。不自动覆盖旧记录。" }),
								/* @__PURE__ */ p("li", { children: "主动取消不退创建费；系统故障导致一题都无法完成时，退本场积分或恢复免费次数。" })
							]
						}),
						/* @__PURE__ */ p("button", {
							className: "button primary",
							disabled: L || !g || g.savedCount >= 2,
							onClick: () => void ke(),
							children: L ? "正在创建…" : g && g.savedCount >= 2 ? "请先手动删除旧记录" : "创建模拟面试 →"
						})
					]
				})]
			}),
			/* @__PURE__ */ m("section", {
				className: "mock-history",
				children: [
					/* @__PURE__ */ p("h2", { children: "我的模拟面试" }),
					l.length === 0 && /* @__PURE__ */ p("p", { children: "你的每一次练习，都会从这里开始。" }),
					l.map((e) => /* @__PURE__ */ m("article", {
						className: "mock-panel",
						children: [
							/* @__PURE__ */ m("div", { children: [/* @__PURE__ */ p("h3", { children: e.title }), /* @__PURE__ */ m("p", { children: [
								_[e.state.phase],
								" · ",
								new Date(e.createdAtMs).toLocaleString("zh-CN")
							] })] }),
							/* @__PURE__ */ p(n, {
								className: "button",
								to: `/app/mock-interviews/${e.sessionId}`,
								children: e.state.phase === "completed" ? "查看报告" : "继续面试"
							}),
							e.state.phase === "completed" && /* @__PURE__ */ p("button", {
								className: "button",
								disabled: L,
								onClick: () => void Z(async () => {
									window.confirm("删除本场问答和报告？不会退还已使用积分或免费次数。") && (await s(`/mock-interviews/${e.sessionId}`, void 0, "DELETE"), await X());
								}),
								children: "删除"
							})
						]
					}, e.sessionId))
				]
			})
		]
	});
	if (!y) return /* @__PURE__ */ m("main", {
		className: "app-page mock-page",
		children: [/* @__PURE__ */ p("h1", { children: "正在恢复面试…" }), F && /* @__PURE__ */ p("p", {
			role: "alert",
			children: F
		})]
	});
	let Q = y.state.phase, $ = y.state.rounds.at(-1);
	return /* @__PURE__ */ m("main", {
		className: "app-page mock-page",
		children: [
			/* @__PURE__ */ m("header", {
				className: "mock-page-heading",
				children: [/* @__PURE__ */ m("div", { children: [
					/* @__PURE__ */ p(n, {
						to: "/app/mock-interviews",
						children: "← 我的模拟面试"
					}),
					/* @__PURE__ */ p("h1", { children: y.title }),
					/* @__PURE__ */ m("p", { children: [y.billingClass === "daily_pass_free" ? "本场全程免费" : "创建费用 100 积分", y.refunded ? " · 本场已退还" : ""] }),
					/* @__PURE__ */ p("p", { children: y.deadlineAtMs ? /* @__PURE__ */ m(h, { children: [
						"本场结束时间：",
						new Date(y.deadlineAtMs).toLocaleString("zh-CN", {
							timeZone: "Asia/Shanghai",
							year: "numeric",
							month: "2-digit",
							day: "2-digit",
							hour: "2-digit",
							minute: "2-digit",
							hour12: !1
						}),
						"（北京时间） · 暂停、等待和重连不延长"
					] }) : /* @__PURE__ */ m(h, { children: [
						"开始后 ",
						y.durationLimitMinutes ?? 60,
						" 分钟自动结束，准备阶段不计时。"
					] }) })
				] }), /* @__PURE__ */ p("span", {
					className: "mock-pill",
					children: _[Q]
				})]
			}),
			F && /* @__PURE__ */ p("p", {
				role: "alert",
				className: "mock-alert",
				children: F
			}),
			Q !== "completed" && !j && /* @__PURE__ */ p("button", {
				className: "button",
				onClick: () => Ce((e) => e + 1),
				children: "重新连接"
			}),
			y.endReason === "time_limit" && /* @__PURE__ */ m("p", {
				role: "status",
				className: "mock-alert",
				children: [
					"已达到本场 ",
					y.durationLimitMinutes ?? 60,
					" 分钟时限，模拟面试已自动结束。已提交的回答将保存在报告中。"
				]
			}),
			Q === "completed" ? /* @__PURE__ */ p(ae, { session: y }) : /* @__PURE__ */ m("div", {
				className: "mock-workbench",
				children: [/* @__PURE__ */ m("aside", {
					className: `mock-portrait ${ve ? "is-speaking" : ""}`,
					children: [/* @__PURE__ */ p("img", {
						src: "/assets/mock-interview/interviewer-v1.png",
						alt: "AI 模拟面试官"
					}), /* @__PURE__ */ m("div", { children: [
						/* @__PURE__ */ p("span", {
							className: "mock-pill",
							children: "AI 模拟面试官 · 非真人"
						}),
						/* @__PURE__ */ p("h2", { children: _[Q] }),
						/* @__PURE__ */ p(re, {
							player: G.current,
							phase: Q
						}),
						/* @__PURE__ */ p("p", { children: "基于你的简历与你对话，不代表真实招聘结果。" })
					] })]
				}), /* @__PURE__ */ m("section", {
					className: "mock-panel mock-conversation",
					children: [Q === "preparing" ? /* @__PURE__ */ m(h, { children: [
						/* @__PURE__ */ p("span", {
							className: "eyebrow",
							children: "开始前检查"
						}),
						/* @__PURE__ */ p("h2", { children: "让这场面试围绕你展开" }),
						/* @__PURE__ */ m("label", { children: ["选择已解析的简历", /* @__PURE__ */ m("select", {
							"aria-label": "选择简历",
							value: y.resumeId ?? "",
							disabled: L || !j,
							onChange: (t) => void Z(async () => {
								let n = b.find((e) => e.documentId === t.target.value);
								n && we(await s(`/mock-interviews/${e}/resume`, {
									version: y.state.version,
									documentId: n.documentId,
									documentVersionId: n.documentVersionId
								}));
							}),
							children: [/* @__PURE__ */ p("option", {
								value: "",
								children: "请选择简历"
							}), b.map((e) => /* @__PURE__ */ p("option", {
								value: e.documentId,
								children: e.displayName
							}, e.documentId))]
						})] }),
						b.length === 0 && /* @__PURE__ */ p("p", { children: /* @__PURE__ */ p(n, {
							to: "/app/library",
							children: "先去资料页上传并解析简历"
						}) }),
						/* @__PURE__ */ m("label", { children: ["桌面助手机器码", /* @__PURE__ */ p("input", {
							inputMode: "numeric",
							maxLength: 6,
							value: le,
							onChange: (e) => ue(e.target.value.replace(/\D/g, "")),
							placeholder: "6 位机器码"
						})] }),
						/* @__PURE__ */ p("p", {
							className: "mock-muted",
							children: "现有正式版助手即可，无需为模拟面试升级。请开启麦克风权限和系统自动校时，建议佩戴耳机。"
						}),
						/* @__PURE__ */ p("p", {
							className: "mock-muted",
							children: "仅使用麦克风，不使用系统声音。助手在提问期间可能仍采集上传，服务器会丢弃非回答时段的音频，不转写、不保存。"
						}),
						/* @__PURE__ */ p("button", {
							className: "button",
							disabled: L || !j || le.length !== 6,
							onClick: () => void Oe(),
							children: "验证并连接"
						}),
						/* @__PURE__ */ p("p", {
							role: "status",
							"aria-label": "助手连接状态",
							children: j ? me || (fe == null ? void 0 : fe.message) || (S ? "● 助手已连接，开始后连接收音通道" : "请打开桌面助手，输入机器码后验证并连接。") : "页面连接未就绪，请重新连接。"
						}),
						/* @__PURE__ */ p("button", {
							className: "button primary",
							disabled: !j || !S || !y.resumeId || L,
							onClick: () => void G.current.unlock().then(() => Y("start")).catch((e) => I(v(e))),
							children: "开始模拟面试 →"
						})
					] }) : /* @__PURE__ */ m(h, { children: [
						/* @__PURE__ */ m("div", {
							className: "mock-question-meta",
							children: [/* @__PURE__ */ m("span", { children: [
								"问题 ",
								y.state.rounds.length,
								" / 10"
							] }), /* @__PURE__ */ p("span", { children: S ? "麦克风助手在线" : "助手未连接" })]
						}),
						$ && /* @__PURE__ */ p("h2", {
							className: "mock-question",
							children: $.question
						}),
						(Q === "generating_question" || Q === "generating_report") && /* @__PURE__ */ m("div", {
							role: "status",
							className: "mock-wait",
							children: [
								/* @__PURE__ */ p("span", { className: "mock-spinner" }),
								_[Q],
								/* @__PURE__ */ p("small", { children: "请稍候，不额外收费，无需重复创建。" })
							]
						}),
						y.error === "generation_unavailable" && /* @__PURE__ */ p("button", {
							className: "button",
							disabled: !j,
							onClick: () => Y("retry"),
							children: "重试生成"
						}),
						w && Q === "speaking" && /* @__PURE__ */ p("p", {
							role: "status",
							className: "mock-wait",
							children: "正在等待助手收音通道连接。请保持助手运行，显示“轮到你回答”后再开口。"
						}),
						E && Q === "speaking" && /* @__PURE__ */ p("p", {
							role: "status",
							className: "mock-wait",
							children: "正在准备收音，请稍候片刻，显示“轮到你回答”后再开口。"
						}),
						Q === "speaking" && /* @__PURE__ */ m("div", {
							className: "mock-actions",
							children: [/* @__PURE__ */ p("button", {
								className: "button primary",
								disabled: !j || ve || w || E,
								onClick: () => {
									A.current = null, q.current = ($ == null ? void 0 : $.question_id) ?? null, G.current.stop(), J.current = !1, B(!0), G.current.unlock().then(() => Y("speak")).catch((e) => I(v(e)));
								},
								children: "朗读问题"
							}), /* @__PURE__ */ p("button", {
								className: "button",
								disabled: !j || w || E,
								onClick: () => {
									G.current.stop(), q.current = null, $ && Ee($.question_id);
								},
								children: "我已读完，开始回答"
							})]
						}),
						(Q === "listening" || Q === "paused") && /* @__PURE__ */ m(h, { children: [/* @__PURE__ */ m("label", { children: ["你的回答", /* @__PURE__ */ p("textarea", {
							"aria-label": "你的回答",
							rows: 8,
							value: N,
							maxLength: 8e3,
							onChange: (e) => {
								U.current = !0, ge(!0), W.current = e.target.value, P(e.target.value);
							},
							placeholder: "请对着麦克风回答，也可在这里校正转写。"
						})] }), /* @__PURE__ */ p("p", {
							className: "mock-muted",
							children: he ? "已进入文字校正，新的转写不会覆盖你的修改。" : "思考和停顿不会自动进入下一题。确认回答后再提交。"
						})] }),
						/* @__PURE__ */ m("div", {
							className: "mock-actions",
							children: [Q === "listening" && /* @__PURE__ */ m(h, { children: [
								/* @__PURE__ */ p("button", {
									className: "button primary",
									disabled: !j || !N.trim(),
									onClick: () => {
										xe.current ??= crypto.randomUUID(), Y("submit", {
											answer: N.trim(),
											submissionId: xe.current
										});
									},
									children: "回答完成 →"
								}),
								/* @__PURE__ */ p("button", {
									className: "button",
									onClick: () => Y("pause"),
									disabled: !j,
									children: "暂停"
								}),
								/* @__PURE__ */ p("button", {
									className: "button",
									onClick: () => Y("replay"),
									disabled: !j,
									children: "重新听题"
								})
							] }), Q === "paused" && /* @__PURE__ */ p("button", {
								className: "button primary",
								disabled: !j || !S,
								onClick: () => Y("resume"),
								children: "继续本题"
							})]
						})
					] }), /* @__PURE__ */ m("footer", {
						className: "mock-end",
						children: [/* @__PURE__ */ p("p", { children: "结束后自动保存报告。不足 10 题将标注为部分练习。" }), /* @__PURE__ */ p("button", {
							className: "button",
							disabled: !j || Q === "generating_report",
							onClick: () => {
								window.confirm("结束本场练习并生成报告？主动结束不退创建费。") && (G.current.stop(), Y("end"));
							},
							children: "结束面试"
						})]
					})]
				})]
			})
		]
	});
}
function ae({ session: e }) {
	let t = e.report, [r, i] = d(!1), [a, o] = d(null), s = f(!1), c = async () => {
		if (!(s.current || e.state.phase !== "completed" || !t)) {
			s.current = !0, i(!0), o(null);
			try {
				let { downloadMockInterviewWord: t } = await import("./mock-interview-word-export-BOxeSAD1.js");
				await t(e);
			} catch {
				o("Word 下载失败，请重试。在线报告不受影响。");
			} finally {
				s.current = !1, i(!1);
			}
		}
	};
	return /* @__PURE__ */ m("section", {
		className: "mock-report",
		children: [
			e.state.phase === "completed" && t && /* @__PURE__ */ m("div", {
				className: "mock-report-actions",
				children: [/* @__PURE__ */ p("button", {
					className: "button primary",
					disabled: r,
					"aria-busy": r,
					onClick: () => void c(),
					children: r ? "正在生成 Word…" : "下载 Word"
				}), /* @__PURE__ */ p("span", {
					className: "mock-muted",
					children: "包含评分、逐题问答与改进建议 · 下载不额外扣费"
				})]
			}),
			a && /* @__PURE__ */ p("p", {
				role: "alert",
				className: "mock-alert",
				children: a
			}),
			/* @__PURE__ */ m("div", {
				className: "mock-panel mock-report-summary",
				children: [/* @__PURE__ */ m("div", {
					className: "mock-score",
					children: [(t == null ? void 0 : t.overall_score) ?? "—", /* @__PURE__ */ p("small", { children: (t == null ? void 0 : t.overall_score) == null ? "有效回答不足，不评分" : "/ 100" })]
				}), /* @__PURE__ */ m("div", { children: [
					/* @__PURE__ */ p("span", {
						className: "eyebrow",
						children: e.partial ? "部分练习报告" : "面试练习报告"
					}),
					/* @__PURE__ */ p("h2", { children: "复盘，让下一次更好。" }),
					/* @__PURE__ */ p("p", { children: t == null ? void 0 : t.summary }),
					/* @__PURE__ */ p("p", {
						className: "mock-muted",
						children: l
					})
				] })]
			}),
			(t == null ? void 0 : t.dimensions) && /* @__PURE__ */ p("div", {
				className: "mock-dimensions",
				children: Object.entries(t.dimensions).map(([e, t]) => /* @__PURE__ */ m("div", {
					className: "mock-panel",
					children: [
						/* @__PURE__ */ p("span", { children: ee[e] ?? e }),
						/* @__PURE__ */ p("strong", { children: t }),
						/* @__PURE__ */ p("meter", {
							min: 0,
							max: 100,
							value: t,
							"aria-label": ee[e] ?? e
						})
					]
				}, e))
			}),
			e.state.rounds.map((e, n) => {
				let r = t == null ? void 0 : t.feedback.find((t) => t.question_id === e.question_id);
				return /* @__PURE__ */ m("article", {
					className: "mock-panel",
					children: [
						/* @__PURE__ */ m("span", {
							className: "eyebrow",
							children: ["问题 ", n + 1]
						}),
						/* @__PURE__ */ p("h3", { children: e.question }),
						/* @__PURE__ */ p("p", {
							className: "mock-answer",
							children: e.answer ?? "本题未提交回答，不计分。"
						}),
						r && /* @__PURE__ */ m(h, { children: [
							/* @__PURE__ */ p("h4", { children: "回答中的证据" }),
							/* @__PURE__ */ p("blockquote", { children: r.answer_quote }),
							/* @__PURE__ */ p("h4", { children: "做得好的地方" }),
							/* @__PURE__ */ p("p", { children: r.strength }),
							/* @__PURE__ */ p("h4", { children: "可以提升" }),
							/* @__PURE__ */ p("p", { children: r.improvement }),
							/* @__PURE__ */ p("h4", { children: "回答建议" }),
							/* @__PURE__ */ p("p", { children: r.suggestion })
						] })
					]
				}, e.question_id);
			}),
			!!(t != null && t.practice_priorities.length) && /* @__PURE__ */ m("section", {
				className: "mock-panel",
				children: [/* @__PURE__ */ p("h3", { children: "下一次练习重点" }), /* @__PURE__ */ p("ul", { children: t.practice_priorities.map((e, t) => /* @__PURE__ */ p("li", { children: e }, t)) })]
			}),
			/* @__PURE__ */ p(n, {
				className: "button",
				to: "/app/mock-interviews",
				children: "返回我的模拟面试"
			})
		]
	});
}
//#endregion
export { ie as MockInterviewPage, ae as MockReportView, _ as mockPhaseLabel };
