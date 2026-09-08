import React from "react";
import { Soundtrack } from "./audio";
import {
  AbsoluteFill,
  Audio,
  Easing,
  Img,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { PageCam, type CamKey } from "./lib/PageCam";
import layout from "../public/textures/layout.json";
export const FPS = 60,
  TOTAL = 2160;
export const SHOTS = {
  open: { from: 0, duration: 239 },
  context: { from: 239, duration: 304 },
  listen: { from: 543, duration: 360 },
  answer: { from: 903, duration: 416 },
  screen: { from: 1319, duration: 415 },
  outro: { from: 1734, duration: 426 },
};
const C = {
  bg: "#080c13",
  surface: "#101721",
  brand: "#6ee7bd",
  text: "#edf2f8",
  muted: "#8f9db0",
  line: "rgba(152,169,190,.22)",
};
const FONT =
  'Inter, "PingFang SC", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const ease = Easing.bezier(0.22, 1, 0.36, 1);
const smooth = Easing.bezier(0.35, 0, 0.25, 1);
const p = (f: number, a: number, b: number) =>
  interpolate(f, [a, b], [0, 1], { ...clamp, easing: ease });
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const tex = (s: string) => staticFile(`textures/${s}.png`);
const shadow =
  "0 40px 100px rgba(0,0,0,.6), 0 1px 0 rgba(255,255,255,.14) inset";
type Rect = { x: number; y: number; w: number; h: number };
const L = layout.live.elements;
const Brand: React.FC<{ size?: number }> = ({ size = 36 }) => (
  <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
    <Img
      src={staticFile("brand/app-icon.png")}
      style={{
        width: size + 8,
        height: size + 8,
        borderRadius: (size + 8) * 0.24,
      }}
    />
    <b style={{ fontSize: size, fontWeight: 700, letterSpacing: "-.035em" }}>
      OfferSteady
    </b>
  </div>
);
const Frame: React.FC<{ children: React.ReactNode; section?: string }> = ({
  children,
  section,
}) => (
  <AbsoluteFill
    style={{
      background: C.bg,
      color: C.text,
      fontFamily: FONT,
      overflow: "hidden",
    }}
  >
    <AbsoluteFill
      style={{
        background:
          "radial-gradient(ellipse 950px 550px at 50% 54%,rgba(37,103,94,.18),transparent 75%), radial-gradient(ellipse 650px 400px at 80% 8%,rgba(61,95,142,.09),transparent 75%)",
      }}
    />
    <div style={{ position: "absolute", left: 84, top: 45, zIndex: 40 }}>
      <Brand size={29} />
    </div>
    <div
      style={{
        position: "absolute",
        right: 84,
        top: 59,
        fontSize: 18,
        color: C.muted,
        letterSpacing: ".12em",
        zIndex: 40,
      }}
    >
      {section ?? "AI INTERVIEW ASSISTANT"}
    </div>
    {children}
    <div
      style={{
        position: "absolute",
        left: 84,
        bottom: 31,
        fontSize: 32,
        color: "#8f9db0",
        zIndex: 40,
      }}
    >
      PRODUCT DEMO · SYNTHETIC EXAMPLE
    </div>
    <div
      style={{
        position: "absolute",
        right: 84,
        bottom: 31,
        fontSize: 16,
        color: "#68788a",
        letterSpacing: ".16em",
        zIndex: 40,
      }}
    >
      OFFERSTEADY
    </div>
  </AbsoluteFill>
);
const Head: React.FC<{ title: string; sub?: string; cue?: number }> = ({
  title,
  sub,
  cue = 12,
}) => {
  const f = useCurrentFrame(),
    v = p(f, cue, cue + 38);
  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        top: 136,
        textAlign: "center",
        zIndex: 30,
        opacity: v,
        transform: `translateY(${18 * (1 - v)}px)`,
      }}
    >
      <div style={{ fontSize: 66, fontWeight: 650, letterSpacing: "-.045em" }}>
        {title}
      </div>
      {sub ? (
        <div
          style={{
            fontSize: 34,
            color: C.muted,
            marginTop: 18,
            letterSpacing: ".025em",
          }}
        >
          {sub}
        </div>
      ) : null}
    </div>
  );
};
const Caption: React.FC<{ children: React.ReactNode; cue?: number }> = ({
  children,
  cue = 20,
}) => {
  const f = useCurrentFrame();
  return (
    <div
      style={{
        position: "absolute",
        left: 80,
        right: 80,
        bottom: 86,
        textAlign: "center",
        fontSize: 60,
        color: "#bdcbd8",
        fontWeight: 450,
        opacity: p(f, cue, cue + 36),
        zIndex: 35,
      }}
    >
      {children}
    </div>
  );
};
const Crop: React.FC<{
  src: string;
  rect: Rect;
  width: number;
  style?: React.CSSProperties;
}> = ({ src, rect, width, style }) => {
  const z = width / rect.w;
  return (
    <div
      style={{
        width,
        height: rect.h * z,
        overflow: "hidden",
        position: "relative",
        ...style,
      }}
    >
      <Img
        src={tex(src)}
        style={{
          position: "absolute",
          width: 1920 * z,
          maxWidth: "none",
          left: -rect.x * z,
          top: -rect.y * z,
        }}
      />
    </div>
  );
};
const Cursor: React.FC<{ x: number; y: number; click?: number }> = ({
  x,
  y,
  click = 0,
}) => (
  <div
    style={{
      position: "absolute",
      left: x,
      top: y,
      zIndex: 50,
      transform: `scale(${1 - 0.14 * click})`,
      transformOrigin: "0 0",
    }}
  >
    {click > 0 ? (
      <div
        style={{
          position: "absolute",
          left: -26,
          top: -26,
          width: 60,
          height: 60,
          border: `2px solid ${C.brand}`,
          borderRadius: "50%",
          opacity: click,
        }}
      />
    ) : null}
    <svg width="38" height="46" viewBox="0 0 38 46">
      <path
        d="M3 2 L31 27 L19 29 L14 41 Z"
        fill="#edf2f8"
        stroke="#080c13"
        strokeWidth="3"
      />
    </svg>
  </div>
);
const SceneGate: React.FC<{ duration: number; children: React.ReactNode }> = ({
  duration,
  children,
}) => {
  const f = useCurrentFrame();
  const alpha = interpolate(
    f,
    [0, 12, duration - 13, duration - 1],
    [0, 1, 1, 0],
    clamp,
  );
  return <AbsoluteFill style={{ opacity: alpha }}>{children}</AbsoluteFill>;
};
const Open: React.FC = () => {
  const f = useCurrentFrame();
  const keys: CamKey[] = [
    { frame: 0, cx: 1365, cy: 971, zoom: 0.96, rotY: -13, rotX: 8 },
    { frame: 75, cx: 1365, cy: 971, zoom: 0.96, rotY: -9, rotX: 6 },
    { frame: 192, cx: 960, cy: 505, zoom: 0.55, rotY: 0, rotX: 5 },
    { frame: 239, cx: 960, cy: 505, zoom: 0.55, rotY: 0, rotX: 5 },
  ];
  return (
    <Frame>
      <div style={{ position: "absolute", inset: 0, top: 50 }}>
        <PageCam
          src="textures/live-full.png"
          pageH={1080}
          keys={keys}
          pageOpacity={p(f, 140, 190)}
        >
          <Img
            src={tex("live-answer-action-bar")}
            style={{
              position: "absolute",
              left: L["answer-action-bar"].x,
              top: L["answer-action-bar"].y,
              width: L["answer-action-bar"].w,
              height: L["answer-action-bar"].h,
              borderRadius: 16,
              boxShadow: `0 0 0 1px rgba(110,231,189,${0.5 * (1 - p(f, 110, 175))}),0 16px 65px rgba(0,0,0,.5)`,
            }}
          />
        </PageCam>
      </div>
      <Head
        title="Stay ready for every question."
        sub="Live transcription · Grounded guidance · Screen Assist"
        cue={18}
      />
      <Caption cue={105}>Your AI interview assistant</Caption>
    </Frame>
  );
};
const Context: React.FC = () => {
  const f = useCurrentFrame();
  const d = interpolate(f, [25, 230], [0, 180], { ...clamp, easing: smooth });
  return (
    <Frame section="01 / YOUR CONTEXT">
      <Head
        title="Ground every answer in your experience."
        sub="Connect your resume, target role, and knowledge materials"
      />
      <div
        style={{
          position: "absolute",
          left: 155 - d * 0.35,
          top: 315,
          width: 1560,
          opacity: 0.16,
          filter: "blur(2px) saturate(.92)",
          transform: "perspective(1800px) rotateY(-8deg) rotateX(6deg)",
        }}
      >
        <Img
          src={tex("library-full")}
          style={{ width: "100%", borderRadius: 20 }}
        />
      </div>
      {[0, 1, 2].map((i) => {
        const v = p(f, 35 + i * 27, 102 + i * 27);
        const r = layout.library.elements[`material-${i}` as "material-0"]!;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: 375 + (1 - v) * (500 + i * 170) - d * 0.7,
              top: 332 + i * 161,
              opacity: v,
              transform: `perspective(1800px) rotateY(${lerp(-22, -4, v)}deg) rotateX(${lerp(8, 0, v)}deg) translateZ(${i * 12}px)`,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 33 }}>
              <div
                style={{
                  width: 190,
                  fontSize: 30,
                  fontWeight: 600,
                  color: i === 1 ? "#82b4ff" : C.brand,
                }}
              >
                {["RESUME", "TARGET ROLE", "KNOWLEDGE"][i]}
              </div>
              <div
                style={{
                  width: 1050,
                  position: "relative",
                  padding: "18px 20px",
                  borderRadius: 20,
                  background: C.surface,
                  border: `1px solid ${C.line}`,
                  boxShadow: shadow,
                }}
              >
                <Img
                  src={tex(`material-${i}`)}
                  style={{
                    display: "block",
                    width: 1010,
                    height: Math.min(126, (r.h * 1010) / r.w),
                    objectFit: "cover",
                    objectPosition: "top",
                    opacity: 0.1,
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    left: 40,
                    top: 27,
                    fontSize: 36,
                    fontWeight: 550,
                    color: C.text,
                  }}
                >
                  {
                    [
                      "Senior Frontend Engineer Resume",
                      "Target Role: Senior Frontend Engineer",
                      "Frontend Performance Playbook",
                    ][i]
                  }
                </div>
                <div
                  style={{
                    position: "absolute",
                    left: 40,
                    top: 80,
                    fontSize: 32,
                    color: C.muted,
                  }}
                >
                  {
                    [
                      "Your experience and project context",
                      "Role priorities and required skills",
                      "Methods, examples, and technical notes",
                    ][i]
                  }
                </div>
              </div>
            </div>
          </div>
        );
      })}
      <div
        style={{
          position: "absolute",
          left: 1740 - d * 1.4,
          top: 365,
          opacity: 0.32,
          filter: "blur(3px)",
        }}
      >
        <Img
          src={tex("material-2")}
          style={{
            width: 450,
            borderRadius: 16,
            transform: "perspective(900px) rotateY(-12deg)",
          }}
        />
      </div>
      <Caption>Relevant to the role. True to your experience.</Caption>
    </Frame>
  );
};
const Listen: React.FC = () => {
  const f = useCurrentFrame(),
    move = p(f, 165, 260);
  const rect = { x: 14, y: 78, w: 779.59375, h: 192 };
  const x = lerp(275, 150, move),
    y = lerp(353, 320, move),
    width = lerp(1370, 1200, move);
  const barW = 1120;
  const click = interpolate(f, [282, 288, 304], [0, 1, 0], clamp);
  return (
    <Frame section="02 / LIVE CONVERSATION">
      <Head
        title="Follow the question as it unfolds."
        sub="Interviewer and candidate transcripts stay separate"
      />
      <div style={{ position: "absolute", inset: 0, opacity: 0.2 }}>
        <PageCam
          src="textures/live-full.png"
          pageH={1080}
          keys={[
            { frame: 0, cx: 960, cy: 500, zoom: 0.69, rotY: 10, rotX: 8 },
            { frame: 359, cx: 960, cy: 500, zoom: 0.69, rotY: -4, rotX: 8 },
          ]}
        />
      </div>
      <div
        style={{
          position: "absolute",
          left: x,
          top: y,
          transform: `perspective(1800px) rotateY(${lerp(8, 0, p(f, 20, 140))}deg)`,
          borderRadius: 20,
          overflow: "hidden",
          boxShadow: shadow,
          border: `1px solid rgba(110,231,189,.36)`,
          background: "#101721",
        }}
      >
        <Crop
          src="live-full"
          rect={rect}
          width={width}
          style={{ opacity: 0.05 }}
        />
        <div
          style={{
            position: "absolute",
            left: 48,
            top: 38,
            fontSize: 32,
            color: C.brand,
          }}
        >
          INTERVIEWER
        </div>
        <div
          style={{
            position: "absolute",
            left: 48,
            right: 48,
            top: 93,
            fontSize: 42,
            lineHeight: 1.5,
          }}
        >
          Tell me about the most challenging
          <br />
          frontend project you have led.
        </div>
        <div
          style={{
            position: "absolute",
            left: 48,
            right: 48,
            bottom: 24,
            fontSize: 32,
            color: "#a5b5c6",
          }}
        >
          YOU: I’ll start with the context and the goal.
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          left: lerp(660, 650, move),
          top: 710,
          opacity: move,
          transform: `translateY(${40 * (1 - move)}px)`,
          borderRadius: 18,
          boxShadow: shadow,
        }}
      >
        <Img
          src={tex("live-answer-action-bar")}
          style={{ display: "block", width: barW, borderRadius: 18 }}
        />
        {f > 215 ? (
          <Cursor
            x={lerp(880, 275, p(f, 220, 282))}
            y={lerp(145, 52, p(f, 220, 282))}
            click={click}
          />
        ) : null}
      </div>
      <Caption>
        {f < 250 ? (
          "Turn spoken questions into context you can follow."
        ) : (
          <span>
            When you’re ready, select <b style={{ color: C.brand }}>Quick Answer</b>.
          </span>
        )}
      </Caption>
    </Frame>
  );
};
const AnswerCard: React.FC<{
  frame: number;
  mode?: "live" | "screenshot";
  width: number;
}> = ({ frame: f, mode = "live", width }) => {
  const r = L["advice-card"];
  const z = width / r.w;
  const s = L["simple-answer"],
    det = L["detailed-answer"];
  const summary = p(f, 36, 60),
    detail = p(f, 88, 116);
  return (
    <div
      style={{
        width,
        height: r.h * z,
        position: "relative",
        borderRadius: 22,
        overflow: "hidden",
        background: C.surface,
        border: `1px solid rgba(110,231,189,${0.3 + interpolate(f, [218, 228, 238], [0, 0.2, 0], clamp)})`,
        boxShadow: shadow,
      }}
    >
      <div
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          width: width,
          height: r.h * z,
        }}
      >
        <Crop src={`${mode}-full`} rect={r} width={width} />
      </div>
      <div
        style={{
          position: "absolute",
          left: (s.x - r.x) * z,
          top: (s.y - r.y) * z,
          width: s.w * z,
          height: (det.y + det.h - s.y) * z,
          background: "#101721",
        }}
      />
      <div
        style={{
          position: "absolute",
          left: (s.x - r.x) * z,
          top: (s.y - r.y) * z,
          opacity: summary,
          clipPath: `inset(0 ${100 * (1 - summary)}% 0 0)`,
        }}
      >
        <Img
          src={tex(`${mode}-simple-answer`)}
          style={{ display: "block", width: s.w * z, height: s.h * z }}
        />
      </div>
      <div
        style={{
          position: "absolute",
          left: (det.x - r.x) * z,
          top: (det.y - r.y) * z,
          opacity: detail,
          clipPath: `inset(0 0 ${100 * (1 - detail)}% 0)`,
        }}
      >
        <Img
          src={tex(`${mode}-detailed-answer`)}
          style={{ width: det.w * z, height: det.h * z, display: "block" }}
        />
      </div>
      {layout[mode].answerRows.map((row, i) => {
        const cue = 116 + [0, 32, 60][i],
          v = p(f, cue, cue + 24);
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: (row.x - r.x) * z,
              top: (row.y - r.y) * z,
              width: row.w * z,
              height: row.h * z,
              background: C.surface,
            }}
          >
            <Img
              src={tex(`${mode}-answer-row-${i}`)}
              style={{
                width: row.w * z,
                height: row.h * z,
                opacity: v,
                transform: `translateY(${18 * (1 - v)}px)`,
                filter: `blur(${6 * (1 - v)}px)`,
              }}
            />
          </div>
        );
      })}
    </div>
  );
};
const Answer: React.FC = () => {
  const f = useCurrentFrame(),
    detail = p(f, 170, 215),
    exit = p(f, 366, 410);
  const simple = L["simple-answer"];
  return (
    <Frame section="03 / ANSWER GUIDANCE">
      <Head
        title="Start clear. Then add the detail."
        sub="A concise answer first, with deeper guidance when you need it"
      />
      <div
        style={{ position: "absolute", inset: 0, opacity: 0.14 + exit * 0.4 }}
      >
        <PageCam
          src="textures/live-full.png"
          pageH={1080}
          keys={[
            { frame: 0, cx: 960, cy: 490, zoom: 0.67, rotY: -8, rotX: 5 },
            { frame: 419, cx: 960, cy: 490, zoom: 0.63, rotY: 0, rotX: 0 },
          ]}
        />
      </div>
      <div
        style={{
          position: "absolute",
          left: 112,
          top: lerp(415, 325, detail),
          width: 1696,
          height: lerp(225, 563, detail),
          borderRadius: 24,
          border: "1px solid rgba(110,231,189,.32)",
          background: "#101721",
          boxShadow: shadow,
          overflow: "hidden",
          opacity: p(f, 0, 40) * (1 - exit),
          transform: `perspective(2000px) rotateY(${lerp(-8, 0, p(f, 0, 55))}deg) translateY(${exit * 30}px)`,
        }}
      >
        <div
          style={{
            position: "absolute",
            left: 48,
            top: 30,
            fontSize: 36,
            color: C.brand,
            fontWeight: 600,
          }}
        >
          {detail < 0.5 ? "SIMPLE ANSWER" : "DETAILED ANSWER"}
        </div>
        <div
          style={{
            position: "absolute",
            left: 48,
            top: 102,
            opacity: p(f, 36, 60) * (1 - detail),
            clipPath: `inset(0 ${100 * (1 - p(f, 36, 60))}% 0 0)`,
          }}
        >
          <Crop
            src="live-full"
            rect={{ x: simple.x, y: simple.y + 66, w: 710, h: 38 }}
            width={1600}
          />
        </div>
        {layout.live.answerRows.map((r, i) => {
          const v = p(f, 215 + [0, 32, 60][i], 239 + [0, 32, 60][i]);
          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: 48,
                top: 99 + i * 143,
                opacity: v,
                transform: `translateY(${18 * (1 - v)}px)`,
                filter: `blur(${6 * (1 - v)}px)`,
              }}
            >
              <Crop src="live-full" rect={{ ...r, w: 710 }} width={1600} />
            </div>
          );
        })}
      </div>
      <Caption>Shape a structured answer from your selected materials.</Caption>
    </Frame>
  );
};
const Problem: React.FC = () => (
  <div
    style={{
      width: 970,
      height: 550,
      border: `1px solid ${C.line}`,
      borderRadius: 22,
      background: "linear-gradient(145deg,#141f2c,#0c131d)",
      padding: 46,
      boxShadow: shadow,
    }}
  >
    <div style={{ fontSize: 18, letterSpacing: ".16em", color: C.brand }}>
      SYSTEM DESIGN
    </div>
    <h2
      style={{
        fontSize: 41,
        lineHeight: 1.4,
        margin: "32px 0 16px",
        fontWeight: 600,
      }}
    >
      Design a flash-sale system that
      <br />
      prevents overselling at high concurrency.
    </h2>
    <div style={{ fontSize: 34, color: "#a1b1c3" }}>
      Explain traffic control, inventory consistency, and failure recovery.
    </div>
    <div
      style={{ display: "flex", alignItems: "center", gap: 18, marginTop: 38 }}
    >
      {["User Requests", "Inventory Service", "Order System"].map((s, i) => (
        <React.Fragment key={s}>
          {i > 0 ? (
            <span style={{ color: C.brand, fontSize: 30 }}>→</span>
          ) : null}
          <div
            style={{
              padding: "23px 24px",
              border: "1px solid rgba(110,231,189,.3)",
              background: "rgba(110,231,189,.045)",
              borderRadius: 14,
              fontSize: 38,
            }}
          >
            {s}
          </div>
        </React.Fragment>
      ))}
    </div>

  </div>
);
const Screen: React.FC = () => {
  const f = useCurrentFrame(),
    v = p(f, 165, 230);
  const click = interpolate(f, [133, 140, 157], [0, 1, 0], clamp);
  return (
    <Frame section="04 / SCREEN ASSIST">
      <Head
        title="Turn an on-screen prompt into a plan."
        sub="Capture the question, then keep the guidance in your workspace"
      />
      <div
        style={{
          position: "absolute",
          left: lerp(455, 120, v),
          top: 330,
          transform: `perspective(1800px) rotateY(${lerp(-9, 6, v)}deg) scale(${lerp(1, 0.86, v)})`,
          transformOrigin: "0 0",
          opacity: 1 - v * 0.37,
        }}
      >
        <Problem />
        {f > 145 && f < 230 ? (
          <div
            style={{
              position: "absolute",
              left: 14,
              right: 14,
              top: 14 + ((f - 145) / 85) * 540,
              height: 2,
              background: C.brand,
              boxShadow: "0 0 16px #6ee7bd",
              opacity: 1 - p(f, 210, 230),
            }}
          />
        ) : null}
      </div>
      <div
        style={{
          position: "absolute",
          left: 510,
          top: 814,
          opacity: 1 - v,
          transform: `translateY(${-20 * v}px)`,
        }}
      >
        <Img
          src={tex("live-answer-action-bar")}
          style={{ width: 1050, borderRadius: 18 }}
        />
        {f > 55 ? (
          <Cursor
            x={lerp(950, 775, p(f, 65, 133))}
            y={lerp(145, 48, p(f, 65, 133))}
            click={click}
          />
        ) : null}
      </div>
      <div
        style={{
          position: "absolute",
          left: lerp(1260, 775, v),
          top: 340,
          opacity: v,
          background: "#101721",
          borderRadius: 22,
          overflow: "hidden",
          boxShadow: shadow,
          transform: `perspective(1800px) rotateY(${lerp(-20, -3, v)}deg)`,
        }}
      >
        <div style={{ opacity: 0.065, filter: "blur(2px)" }}>
          <AnswerCard mode="screenshot" frame={(f - 165) * 1.16} width={1030} />
        </div>
        <div
          style={{
            position: "absolute",
            left: 45,
            top: 35,
            fontSize: 36,
            color: C.brand,
          }}
        >
          APPROACH
        </div>
        {[
          ["Rate-limit traffic", "Reject invalid requests before core services"],
          ["Reserve atomically", "Keep inventory consistent and idempotent"],
          ["Create orders async", "Absorb bursts and recover after failures"],
        ].map(([title, body], i) => (
          <div
            key={title}
            style={{
              position: "absolute",
              left: 45,
              top: 106 + i * 114,
              opacity: p(f, 225 + i * 24, 249 + i * 24),
            }}
          >
            <div style={{ fontSize: 42, fontWeight: 600, color: C.text }}>
              {title}
            </div>
            <div style={{ fontSize: 32, marginTop: 9, color: "#9eb1c3" }}>
              {body}
            </div>
          </div>
        ))}
      </div>
      <Caption>
        {f < 165 ? (
          <span>
            Select <b style={{ color: C.brand }}>Screen Assist</b> to analyse the prompt.
          </span>
        ) : (
          "Understand the prompt. Build a clear path forward."
        )}
      </Caption>
    </Frame>
  );
};
const Outro: React.FC = () => {
  const f = useCurrentFrame(),
    assemble = p(f, 0, 65),
    clean = p(f, 120, 190),
    brand = p(f, 140, 210);
  const items = [
    { s: "material-0", x: 60, y: 265, w: 610, r: -9 },
    { s: "live-answer-action-bar", x: 1200, y: 250, w: 630, r: 7 },
    { s: "live-advice-card", x: 110, y: 610, w: 620, r: 6 },
    { s: "screenshot-simple-answer", x: 1180, y: 650, w: 610, r: -7 },
  ];
  return (
    <Frame section="READY FOR WHAT COMES NEXT">
      {items.map((a, i) => (
        <div
          key={a.s}
          style={{
            position: "absolute",
            left: lerp(a.x + (i % 2 ? 450 : -450), a.x, assemble),
            top: a.y,
            opacity: assemble * (1 - clean) * 0.75,
            transform: `perspective(1200px) rotateY(${a.r}deg) translateY(${clean * (i < 2 ? -160 : 160)}px)`,
            borderRadius: 18,
            overflow: "hidden",
            border: `1px solid ${C.line}`,
            boxShadow: shadow,
          }}
        >
          <Img src={tex(a.s)} style={{ width: a.w, display: "block" }} />
        </div>
      ))}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: lerp(375, 300, brand),
          textAlign: "center",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            transform: `scale(${lerp(0.9, 1, assemble)})`,
            opacity: assemble,
          }}
        >
          <Img
            src={staticFile("brand/app-icon.png")}
            style={{
              width: 112,
              height: 112,
              borderRadius: 27,
              boxShadow: "0 20px 70px rgba(70,193,156,.17)",
            }}
          />
        </div>
        <div
          style={{
            fontSize: 61,
            fontWeight: 700,
            letterSpacing: "-.03em",
            marginTop: 22,
          }}
        >
          OfferSteady
        </div>
        <div
          style={{
            fontSize: 76,
            lineHeight: 1.24,
            fontWeight: 650,
            letterSpacing: "-.045em",
            marginTop: 42,
            opacity: brand,
            transform: `translateY(${24 * (1 - brand)}px)`,
          }}
        >
          Every answer, <span style={{ color: C.brand }}>with more clarity.</span>
        </div>
        <div
          style={{
            fontSize: 36,
            color: "#94a6b9",
            marginTop: 25,
            opacity: brand,
          }}
        >
          Your context · Live guidance · Screen Assist
        </div>
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 32,
            marginTop: 48,
            padding: "19px 35px",
            borderRadius: 15,
            color: "#06241b",
            background: C.brand,
            fontSize: 36,
            fontWeight: 650,
            opacity: p(f, 218, 258),
          }}
        >
          Get ready for your next interview <span>↗</span>
        </div>
      </div>
    </Frame>
  );
};
export type Props = { bgm?: boolean; sfx?: boolean };
export const Commercial: React.FC<Props> = ({ bgm = true, sfx = true }) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      {Object.entries(SHOTS).map(([key, s], i) => {
        const Comp = [Open, Context, Listen, Answer, Screen, Outro][i];
        return (
          <Sequence key={key} from={s.from} durationInFrames={s.duration}>
            <SceneGate duration={s.duration}>
              <Comp />
            </SceneGate>
          </Sequence>
        );
      })}
      <Soundtrack bgm={bgm} sfx={sfx} />
    </AbsoluteFill>
  );
};
