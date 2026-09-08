import React from "react";
import {
  AbsoluteFill,
  Audio,
  Easing,
  Img,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
} from "remotion";

const C = {
  bg: "#080c13",
  surface: "#101721",
  surface2: "#151e2b",
  line: "rgba(152,169,190,.20)",
  text: "#edf2f8",
  muted: "#8f9db0",
  brand: "#6ee7bd",
  blue: "#82b4ff",
  warn: "#f3bd60",
};
const SANS = 'Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif';
const MONO = "SFMono-Regular,Menlo,Monaco,Consolas,monospace";
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const ease = Easing.bezier(0, 0, 0.2, 1);
const land = Easing.bezier(0.34, 1.4, 0.44, 1);

export const SHOTS = {
  brand: { from: 0, duration: 165 },
  listen: { from: 165, duration: 225 },
  context: { from: 390, duration: 210 },
  answer: { from: 600, duration: 270 },
  screenshot: { from: 870, duration: 210 },
  pricing: { from: 1080, duration: 210 },
  review: { from: 1290, duration: 150 },
  outro: { from: 1440, duration: 360 },
} as const;

const fadeWindow = (f: number, d: number) =>
  interpolate(f, [0, 8, d - 8, d], [0, 1, 1, 0], clamp);
const Background: React.FC<{ children?: React.ReactNode }> = ({ children }) => (
  <AbsoluteFill
    style={{
      background: C.bg,
      color: C.text,
      fontFamily: SANS,
      overflow: "hidden",
    }}
  >
    <AbsoluteFill
      style={{
        background:
          "radial-gradient(circle at 70% 4%,rgba(43,157,127,.13),transparent 43rem)",
      }}
    />
    <AbsoluteFill
      style={{
        opacity: 0.42,
        backgroundImage:
          "linear-gradient(rgba(130,180,255,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(130,180,255,.035) 1px,transparent 1px)",
        backgroundSize: "72px 72px",
      }}
    />
    {children}
  </AbsoluteFill>
);
const Caption: React.FC<{
  eyebrow: string;
  children: React.ReactNode;
  align?: "left" | "center";
}> = ({ eyebrow, children, align = "left" }) => (
  <div
    style={{
      position: "absolute",
      left: align === "left" ? 90 : 260,
      right: align === "left" ? 90 : 260,
      bottom: 58,
      textAlign: align,
      zIndex: 20,
      textShadow: "0 3px 16px rgba(0,0,0,.85)",
    }}
  >
    <div
      style={{
        fontFamily: MONO,
        fontWeight: 800,
        fontSize: 32,
        letterSpacing: ".13em",
        color: C.brand,
        marginBottom: 12,
      }}
    >
      {eyebrow}
    </div>
    <div
      style={{
        fontSize: 60,
        fontWeight: 780,
        lineHeight: 1.1,
        letterSpacing: "-.04em",
      }}
    >
      {children}
    </div>
  </div>
);
const ProductPage: React.FC<{
  src: string;
  scale?: number;
  blur?: number;
  dim?: number;
  x?: number;
  y?: number;
}> = ({ src, scale = 1, blur = 0, dim = 0, x = 0, y = 0 }) => (
  <AbsoluteFill
    style={{
      transform: `translate(${x}px,${y}px) scale(${scale})`,
      filter: `blur(${blur}px)`,
      transformOrigin: "50% 50%",
    }}
  >
    <Img
      src={staticFile(src)}
      style={{ width: "100%", height: "100%", objectFit: "cover" }}
    />
    <AbsoluteFill style={{ background: `rgba(4,8,13,${dim})` }} />
  </AbsoluteFill>
);
const Transition: React.FC<{ kind: "A" | "B" | "C" }> = ({ kind }) => {
  const f = useCurrentFrame();
  if (kind === "A") {
    const x = interpolate(f, [0, 12], [-520, 2440], {
      ...clamp,
      easing: Easing.inOut(Easing.cubic),
    });
    return (
      <AbsoluteFill
        style={{
          background: "rgba(223,252,243,.05)",
          backdropFilter: `blur(${interpolate(f, [0, 6, 12], [0, 5, 0], clamp)}px)`,
        }}
      >
        <div
          style={{
            position: "absolute",
            left: x,
            top: -180,
            width: 420,
            height: 1440,
            transform: "rotate(14deg)",
            background:
              "linear-gradient(90deg,transparent,rgba(223,252,243,.72),transparent)",
            filter: "blur(28px)",
          }}
        />
      </AbsoluteFill>
    );
  }
  if (kind === "B") {
    const dark = interpolate(f, [0, 6, 12], [0, 0.96, 0], clamp);
    const line = interpolate(f, [0, 6, 12], [0, 1, 0], clamp);
    return (
      <AbsoluteFill style={{ background: `rgba(3,7,11,${dark})` }}>
        <div
          style={{
            position: "absolute",
            left: "50%",
            top: "50%",
            width: `${320 + line * 1050}px`,
            height: 2,
            transform: "translate(-50%,-50%)",
            background: `rgba(110,231,189,${line * 0.62})`,
            boxShadow: "0 0 28px rgba(110,231,189,.45)",
          }}
        />
      </AbsoluteFill>
    );
  }
  const blur = interpolate(f, [0, 6, 12], [0, 18, 0], clamp);
  return (
    <AbsoluteFill
      style={{
        background: `rgba(8,12,19,${interpolate(f, [0, 6, 12], [0, 0.38, 0], clamp)})`,
        backdropFilter: `blur(${blur}px)`,
      }}
    />
  );
};
const SceneMotion: React.FC<{
  children: React.ReactNode;
  duration: number;
  inKind?: "A" | "B" | "C";
  outKind?: "A" | "B" | "C";
}> = ({ children, duration, inKind, outKind }) => {
  const f = useCurrentFrame();
  const enter = interpolate(f, [0, 12], [0, 1], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  const leave = interpolate(f, [duration - 12, duration], [0, 1], {
    ...clamp,
    easing: Easing.in(Easing.cubic),
  });
  const inScale = inKind === "B" ? 0.72 : inKind === "A" ? 0.96 : 1;
  const outScale = outKind === "B" ? 1.16 : outKind === "A" ? 1.04 : 1;
  const tx =
    (inKind === "B"
      ? 180 * (1 - enter)
      : inKind === "C"
        ? 36 * (1 - enter)
        : 0) +
    (outKind === "B" ? -180 * leave : outKind === "C" ? -36 * leave : 0);
  const scale =
    (inScale + (1 - inScale) * enter) * (1 + (outScale - 1) * leave);
  const blur = (inKind ? 14 * (1 - enter) : 0) + (outKind ? 14 * leave : 0);
  return (
    <AbsoluteFill
      style={{
        transform: `translateX(${tx}px) scale(${scale})`,
        filter: `blur(${blur}px)`,
        opacity: interpolate(
          f,
          [0, 4, duration - 4, duration],
          [inKind ? 0.45 : 1, 1, 1, outKind ? 0.45 : 1],
          clamp,
        ),
      }}
    >
      {children}
    </AbsoluteFill>
  );
};

const BrandScene: React.FC = () => {
  const f = useCurrentFrame();
  const leadIn = interpolate(f, [0, 20], [0, 1], { ...clamp, easing: ease });
  const recede = interpolate(f, [30, 62], [0, 1], {
    ...clamp,
    easing: Easing.bezier(0.5, 0, 0.05, 1),
  });
  const subIn = interpolate(f, [62, 82], [0, 1], { ...clamp, easing: ease });
  const out = interpolate(f, [153, 164], [0, 1], {
    ...clamp,
    easing: Easing.in(Easing.cubic),
  });
  const scale =
    (2.25 + 0.12 * interpolate(f, [0, 30], [0, 1], clamp)) * (1 - recede) +
    recede;
  const y = (1 - recede) * 44 - recede * 62;
  return (
    <Background>
      <div
        style={{
          position: "absolute",
          top: 58,
          right: 70,
          display: "flex",
          alignItems: "center",
          gap: 16,
          opacity: subIn,
        }}
      >
        <Img
          src={staticFile("brand/app-icon.png")}
          style={{ width: 64, height: 64, borderRadius: 17 }}
        />
        <b style={{ fontSize: 34 }}>面试稳</b>
      </div>
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          opacity: (1 - out) * leadIn,
          transform: `translateY(${y}px) scale(${1 - 0.08 * out})`,
        }}
      >
        <div
          style={{
            fontSize: 128,
            fontWeight: 850,
            letterSpacing: "-.07em",
            transform: `scale(${scale})`,
            transformOrigin: "50% 70%",
            color: C.brand,
          }}
        >
          面试稳
        </div>
        <div
          style={{
            fontSize: 104,
            fontWeight: 820,
            letterSpacing: "-.065em",
            marginTop: 16,
            opacity: recede,
            transform: `translateY(${22 * (1 - recede)}px)`,
          }}
        >
          面试就选 <span style={{ color: C.brand }}>面试稳。</span>
        </div>
        <div
          style={{
            fontSize: 38,
            color: "#c2ceda",
            marginTop: 28,
            opacity: subIn,
          }}
        >
          现场听懂问题，回答基于你的真实经历。
        </div>
        <div
          style={{
            fontFamily: MONO,
            fontSize: 32,
            letterSpacing: ".16em",
            color: C.brand,
            marginTop: 34,
            opacity: subIn,
          }}
        >
          LIVE INTERVIEW COPILOT
        </div>
      </AbsoluteFill>
    </Background>
  );
};

const sourceCards = [
  ["简历", "真实经历"],
  ["目标岗位 JD", "岗位要求"],
  ["知识库", "准备材料"],
];
const bezier = (t: number, p0: number, p1: number, p2: number, p3: number) =>
  Math.pow(1 - t, 3) * p0 +
  3 * Math.pow(1 - t, 2) * t * p1 +
  3 * (1 - t) * t * t * p2 +
  t * t * t * p3;
const ContextScene: React.FC = () => {
  const raw = useCurrentFrame();
  const f = Math.max(0, (raw - 10) * 0.72);
  return (
    <Background>
      <ProductPage
        src="textures/live-full.png"
        scale={1.03}
        blur={2}
        dim={0.72}
      />
      <div
        style={{
          position: "absolute",
          inset: "74px 84px 190px",
          border: `1px solid ${C.line}`,
          borderRadius: 26,
          background: "rgba(16,23,33,.88)",
          boxShadow: "0 36px 100px rgba(0,0,0,.38)",
        }}
      >
        <svg
          width="1752"
          height="800"
          viewBox="0 0 1752 800"
          style={{ position: "absolute", inset: 0, overflow: "visible" }}
        >
          {sourceCards.map((_, i) => {
            const y = 160 + i * 210;
            const draw = interpolate(
              f,
              [8 + i * 7, 38 + i * 7, 96, 112],
              [0, 1, 1, 0],
              clamp,
            );
            const packet = interpolate(f, [28 + i * 5, 92 + i * 3], [0, 1], {
              ...clamp,
              easing: Easing.inOut(Easing.cubic),
            });
            const px = bezier(packet, 340, 760, 900, 1310);
            const py = bezier(packet, y, y, 400, 400);
            return (
              <g key={i}>
                <path
                  d={`M 340 ${y} C 760 ${y} 900 400 1310 400`}
                  fill="none"
                  stroke={C.brand}
                  strokeWidth="3"
                  strokeDasharray="1150"
                  strokeDashoffset={1150 * (1 - draw)}
                  opacity={0.4 + 0.5 * draw}
                />
                <circle
                  cx={px}
                  cy={py}
                  r={6}
                  fill={C.brand}
                  opacity={interpolate(
                    f,
                    [28 + i * 5, 36 + i * 5, 94, 104],
                    [0, 1, 1, 0],
                    clamp,
                  )}
                  style={{ filter: "drop-shadow(0 0 9px #6ee7bd)" }}
                />
              </g>
            );
          })}
        </svg>
        {sourceCards.map(([name, sub], i) => {
          const y = 160 + i * 210;
          const enter = interpolate(f, [4 + i * 6, 20 + i * 6], [0, 1], {
            ...clamp,
            easing: land,
          });
          const travel = interpolate(f, [42 + i * 4, 94 + i * 4], [0, 1], {
            ...clamp,
            easing: Easing.inOut(Easing.cubic),
          });
          const x = bezier(travel, 210, 630, 900, 1310);
          const yy = bezier(travel, y, y, 400, 400);
          const absorb = interpolate(f, [82 + i * 4, 98 + i * 4], [0, 1], {
            ...clamp,
            easing: Easing.in(Easing.cubic),
          });
          const size = (1 - 0.75 * Math.pow(travel, 1.6)) * (1 - absorb);
          return (
            <div
              key={name}
              style={{
                position: "absolute",
                left: x - 150,
                top: yy - 56,
                width: 300,
                height: 112,
                border: `1px solid ${C.line}`,
                borderRadius: 18,
                background: C.surface2,
                padding: "16px 24px",
                opacity: enter * (1 - absorb),
                transform: `scale(${enter * size})`,
                boxShadow: "0 18px 55px rgba(0,0,0,.35)",
              }}
            >
              <div style={{ fontSize: 32, fontWeight: 750 }}>{name}</div>
              <div style={{ fontSize: 32, color: C.muted, marginTop: 2 }}>
                {sub}
              </div>
            </div>
          );
        })}
        <div
          style={{
            position: "absolute",
            left: 1244,
            top: 334,
            width: 132,
            height: 132,
            borderRadius: 66,
            display: "grid",
            placeItems: "center",
            background: C.brand,
            boxShadow: `0 0 ${60 * interpolate(f, [70, 98], [0, 1], clamp)}px rgba(110,231,189,.35)`,
            transform: `scale(${1 + interpolate(f, [88, 98, 108], [0, 0.12, 0], clamp)})`,
          }}
        >
          <Img
            src={staticFile("brand/app-icon.png")}
            style={{ width: 88, height: 88, borderRadius: 24 }}
          />
        </div>
      </div>
      <Caption eyebrow="YOUR CONTEXT">回答有依据，表达才更像你。</Caption>
    </Background>
  );
};

const noise = (x: number) => {
  const i = Math.floor(x);
  const s = x - i;
  const hash = (n: number) => {
    const v = Math.sin(n * 91.345 + 17.31) * 43758.5453;
    return v - Math.floor(v);
  };
  const q = s * s * (3 - 2 * s);
  return hash(i) * (1 - q) + hash(i + 1) * q;
};
const ListenScene: React.FC = () => {
  const f = useCurrentFrame();
  const zoom = interpolate(f, [0, 210], [1.06, 1.0], {
    ...clamp,
    easing: ease,
  });
  const collapse = interpolate(f, [176, 190], [1, 0.06], {
    ...clamp,
    easing: Easing.in(Easing.ease),
  });
  const capsuleIn = interpolate(f, [12, 32], [0, 1], {
    ...clamp,
    easing: ease,
  });
  return (
    <Background>
      <ProductPage src="textures/live-full.png" scale={zoom} dim={0.34} />
      <div
        style={{
          position: "absolute",
          left: 255,
          right: 255,
          top: 350,
          height: 250,
          border: "2px solid rgba(255,255,255,.12)",
          borderRadius: 125,
          background: "rgba(12,18,27,.94)",
          backdropFilter: "blur(20px)",
          boxShadow: "0 35px 100px rgba(0,0,0,.58)",
          display: "flex",
          alignItems: "center",
          padding: "0 42px",
          gap: 34,
          opacity: capsuleIn,
          transform: `scale(${1.04 - 0.04 * capsuleIn})`,
        }}
      >
        <div
          style={{
            width: 90,
            height: 90,
            borderRadius: 45,
            display: "grid",
            placeItems: "center",
            background: "rgba(110,231,189,.12)",
            border: "2px solid rgba(110,231,189,.32)",
            fontSize: 44,
          }}
        >
          ◉
        </div>
        <div
          style={{
            height: 170,
            flex: 1,
            display: "flex",
            alignItems: "center",
            gap: 7,
          }}
        >
          {Array.from({ length: 64 }, (_, i) => {
            const sample = f - (63 - i) * 1.6;
            const talk = Math.max(
              interpolate(sample, [24, 32, 78, 88], [0, 1, 1, 0], clamp),
              interpolate(sample, [108, 118, 160, 172], [0, 1, 1, 0], clamp),
            );
            const center = Math.pow(Math.sin((i / 63) * Math.PI), 0.8);
            const h = Math.max(
              6,
              talk *
                (0.4 + 0.6 * noise(sample / 4.5 + i * 0.13)) *
                center *
                145 *
                collapse,
            );
            return (
              <div
                key={i}
                style={{
                  flex: 1,
                  height: h,
                  borderRadius: 4,
                  background: C.brand,
                  opacity: 0.48 + h / 260,
                }}
              />
            );
          })}
        </div>
        <div
          style={{
            width: 90,
            height: 90,
            borderRadius: 45,
            display: "grid",
            placeItems: "center",
            background: C.brand,
            color: "#06241b",
            fontSize: 46,
            transform: `scale(${interpolate(f, [176, 179, 186], [1, 0.82, 1], clamp)})`,
          }}
        >
          ↑
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          top: 92,
          left: 90,
          fontFamily: MONO,
          fontSize: 32,
          color: C.brand,
          letterSpacing: ".12em",
        }}
      >
        由你触发 · 来源可核对
      </div>
      <Caption eyebrow="LIVE CONVERSATION">
        现场听懂问题，跟上面试节奏。
      </Caption>
    </Background>
  );
};

const answerRows = [
  ["回答结构", "背景 → 决策 → 结果"],
  ["简历依据", "跨端工作台与性能治理"],
  ["JD 重点", "复杂产品交付与协作边界"],
  ["知识补充", "监控指标与技术取舍"],
];
const AnswerScene: React.FC = () => {
  const raw = useCurrentFrame();
  const f = Math.max(0, (raw - 18) * 0.64);
  const panel = interpolate(f, [0, 18], [0, 1], { ...clamp, easing: ease });
  const summary = interpolate(f, [18, 32], [0, 1], { ...clamp, easing: ease });
  const pulse = interpolate(f, [106, 112, 120], [0, 1, 0], clamp);
  return (
    <Background>
      <ProductPage
        src="textures/live-answer-workspace.png"
        scale={1.12}
        blur={2}
        dim={0.62}
      />
      <div
        style={{
          position: "absolute",
          left: 270,
          top: 58,
          width: 1380,
          height: 864,
          border: `1px solid ${C.line}`,
          borderRadius: 28,
          background:
            "linear-gradient(145deg,rgba(21,30,43,.99),rgba(10,16,24,.99))",
          padding: "32px 44px",
          boxShadow: `0 0 ${55 * pulse}px rgba(110,231,189,${0.38 * pulse}),0 45px 120px rgba(0,0,0,.62)`,
          opacity: panel,
          transform: `translateY(${18 * (1 - panel)}px) scale(${0.98 + 0.02 * panel})`,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            fontFamily: MONO,
            fontSize: 32,
            color: C.brand,
            letterSpacing: ".10em",
          }}
        >
          AI 回答{" "}
          <span
            style={{
              marginLeft: "auto",
              fontSize: 32,
              color: C.muted,
              letterSpacing: 0,
            }}
          >
            基于已选择资料
          </span>
        </div>
        <div
          style={{
            marginTop: 22,
            paddingBottom: 22,
            borderBottom: `1px solid ${C.line}`,
            fontSize: 42,
            fontWeight: 760,
            lineHeight: 1.32,
            opacity: summary,
            clipPath: `inset(0 ${100 * (1 - summary)}% 0 0)`,
          }}
        >
          先说明项目目标，再聚焦你的技术决策，最后用可核对的结果收尾。
        </div>
        <div style={{ position: "relative", marginTop: 20 }}>
          {answerRows.map(([title, meta], i) => {
            const cue = 48 + [0, 14, 26, 36][i];
            const t = interpolate(f, [cue, cue + 13], [0, 1], {
              ...clamp,
              easing: ease,
            });
            const done = interpolate(f, [cue + 3, cue + 14], [0, 1], clamp);
            return (
              <div
                key={title}
                style={{
                  height: 96,
                  marginBottom: 10,
                  border: `1px solid ${C.line}`,
                  borderRadius: 16,
                  background: "rgba(255,255,255,.025)",
                  display: "flex",
                  alignItems: "center",
                  padding: "0 26px",
                  gap: 20,
                  opacity: t,
                  transform: `translateY(${18 * (1 - t)}px)`,
                  filter: `blur(${6 * (1 - t)}px)`,
                }}
              >
                <div
                  style={{
                    width: 38,
                    height: 38,
                    borderRadius: 19,
                    border: `2px solid ${done > 0.5 ? C.brand : C.muted}`,
                    background: done > 0.5 ? C.brand : "transparent",
                    color: "#06241b",
                    display: "grid",
                    placeItems: "center",
                    fontSize: 26,
                    fontWeight: 900,
                    transform: `scale(${0.78 + 0.22 * done})`,
                  }}
                >
                  {done > 0.5 ? "✓" : "·"}
                </div>
                <div style={{ fontSize: 32, fontWeight: 720 }}>{title}</div>
                <div
                  style={{ marginLeft: "auto", fontSize: 32, color: C.muted }}
                >
                  {meta}
                </div>
              </div>
            );
          })}
        </div>
        <div
          style={{
            fontFamily: MONO,
            fontSize: 32,
            color: C.brand,
            opacity: interpolate(f, [104, 116], [0, 1], clamp),
          }}
        >
          ✓ 回答建议已生成 · 来源可核对
        </div>
      </div>
      <Caption eyebrow="ANSWER WITH CONTEXT">
        关键点先到，回答逻辑随后补齐。
      </Caption>
    </Background>
  );
};

const ScreenshotScene: React.FC = () => {
  const raw = useCurrentFrame();
  const f = Math.max(0, (raw - 8) * 0.64);
  const y = interpolate(f, [8, 90], [-60, 720], clamp);
  const targets = [
    { x: 520, y: 278, w: 290, h: 100, l: "题目目标" },
    { x: 935, y: 260, w: 440, h: 160, l: "关键约束" },
    { x: 655, y: 510, w: 610, h: 125, l: "解题路径" },
  ];
  return (
    <Background>
      <ProductPage
        src="textures/live-full.png"
        scale={1.03}
        blur={1}
        dim={0.55}
      />
      <div
        style={{
          position: "absolute",
          left: 360,
          top: 118,
          width: 1200,
          height: 720,
          border: `1px solid ${C.line}`,
          borderRadius: 26,
          background: C.surface,
          boxShadow: "0 42px 120px rgba(0,0,0,.58)",
          padding: "44px 60px",
        }}
      >
        <div
          style={{
            fontFamily: MONO,
            color: C.brand,
            fontSize: 32,
            letterSpacing: ".10em",
          }}
        >
          SCREENSHOT QUESTION · ANALYZING
        </div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1.15fr",
            gap: 38,
            marginTop: 24,
          }}
        >
          <div
            style={{
              border: `1px solid ${C.line}`,
              borderRadius: 18,
              padding: 24,
              background: "#0b1119",
            }}
          >
            <div style={{ fontSize: 32, color: C.muted }}>
              系统设计题（合成）
            </div>
            <div
              style={{
                fontSize: 38,
                fontWeight: 760,
                lineHeight: 1.35,
                marginTop: 14,
              }}
            >
              设计一个支持百万用户的消息通知系统
            </div>
            <div
              style={{
                height: 12,
                background: "#233040",
                borderRadius: 6,
                marginTop: 24,
              }}
            />
            <div
              style={{
                height: 12,
                width: "78%",
                background: "#233040",
                borderRadius: 6,
                marginTop: 12,
              }}
            />
          </div>
          <div style={{ padding: 14 }}>
            <div style={{ fontSize: 34, fontWeight: 760 }}>识别结果</div>
            <div
              style={{
                fontSize: 32,
                lineHeight: 1.5,
                color: "#c8d2de",
                marginTop: 12,
              }}
            >
              明确容量目标、消息模型与可靠性边界，再讨论队列、存储和降级策略。
            </div>
            <div style={{ display: "flex", gap: 10, marginTop: 18 }}>
              {["容量", "可靠性", "取舍"].map((x) => (
                <span
                  key={x}
                  style={{
                    padding: "8px 15px",
                    border: `1px solid ${C.line}`,
                    borderRadius: 999,
                    color: C.brand,
                    fontSize: 32,
                  }}
                >
                  {x}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
      {targets.map((t) => {
        const pass = 8 + ((t.y + t.h + 60) / 780) * 82;
        const a = interpolate(f, [pass, pass + 12], [0, 1], {
          ...clamp,
          easing: land,
        });
        return (
          <div
            key={t.l}
            style={{
              position: "absolute",
              left: t.x,
              top: t.y,
              width: t.w,
              height: t.h,
              border: `2px solid rgba(110,231,189,${a})`,
              opacity: a,
              transform: `scale(${1.75 - 0.75 * a})`,
            }}
          />
        );
      })}
      {targets.map((t, i) => {
        const pass = 8 + ((t.y + t.h + 60) / 780) * 82;
        const a = interpolate(f, [pass + 4, pass + 14], [0, 1], clamp);
        return (
          <div
            key={`${t.l}-label`}
            style={{
              position: "absolute",
              left: 470 + i * 340,
              top: 850,
              padding: "8px 18px",
              border: `1px solid ${C.line}`,
              borderRadius: 999,
              background: "rgba(8,12,19,.94)",
              fontFamily: MONO,
              fontSize: 32,
              color: C.brand,
              opacity: a,
            }}
          >
            {t.l}
          </div>
        );
      })}
      <div
        style={{
          position: "absolute",
          left: 360,
          width: 1200,
          top: y,
          height: 3,
          background: C.brand,
          boxShadow: "0 0 20px rgba(110,231,189,.8)",
        }}
      />
      <Caption eyebrow="SCREENSHOT ANSWER">截图题，也能快速抓住重点。</Caption>
    </Background>
  );
};

const pricingItems = [
  "免费体验",
  "偶尔使用 · 按次",
  "高频使用 · 按天",
  "按面试节奏选择",
  "成本价使用",
];
const PricingScene: React.FC = () => {
  const f = useCurrentFrame();
  const steps = 4;
  const g = interpolate(f, [22, 150], [0, steps], {
    ...clamp,
    easing: Easing.linear,
  });
  const step = Math.min(steps - 1, Math.floor(g));
  const local = Math.min(1, g - step);
  const hold = 5 / 14;
  const move = Easing.out(Easing.poly(5))(Math.min(1, local / (1 - hold)));
  const pos = step + move;
  const landP = Math.max(0, (local - (1 - hold)) / hold);
  const breath =
    landP > 0 ? Math.sin(Math.min(1, landP / 0.6) * Math.PI) * 0.06 : 0;
  const inP = interpolate(f, [0, 22], [0, 1], { ...clamp, easing: ease });
  return (
    <Background>
      <ProductPage
        src="textures/landing-pricing-full.png"
        scale={1.025}
        dim={0.48}
      />
      <div
        style={{
          position: "absolute",
          left: 250,
          top: 126,
          width: 1420,
          height: 650,
          border: `1px solid ${C.line}`,
          borderRadius: 30,
          background: "rgba(8,13,20,.96)",
          boxShadow: "0 46px 120px rgba(0,0,0,.62)",
          display: "grid",
          gridTemplateColumns: "1.05fr .95fr",
          overflow: "hidden",
          opacity: inP,
          transform: `translateY(${20 * (1 - inP)}px)`,
        }}
      >
        <div
          style={{
            position: "relative",
            overflow: "hidden",
            background: "#080d14",
            display: "grid",
            placeItems: "center",
          }}
        >
          <Img
            src={staticFile("textures/landing-pricing-value.png")}
            style={{
              width: "92%",
              height: "92%",
              objectFit: "contain",
              objectPosition: "center",
              filter: "brightness(.72) saturate(.9)",
            }}
          />
          <AbsoluteFill
            style={{
              background:
                "linear-gradient(90deg,rgba(8,13,20,.08),rgba(8,13,20,.58))",
            }}
          />
        </div>
        <div
          style={{
            position: "relative",
            display: "grid",
            placeItems: "center",
          }}
        >
          <div
            style={{
              position: "relative",
              width: 560,
              height: 360,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                position: "absolute",
                left: 0,
                right: 0,
                top: 144,
                height: 72,
                border: `1px solid rgba(86,230,177,.34)`,
                borderRadius: 999,
                background: "rgba(86,230,177,.10)",
                boxShadow: "0 14px 40px rgba(0,0,0,.28)",
                transform: `scaleY(${1 + breath})`,
              }}
            />
            <div
              style={{
                position: "absolute",
                left: 0,
                right: 0,
                top: 0,
                transform: `translateY(${144 - pos * 72}px)`,
              }}
            >
              {pricingItems.map((item, i) => {
                const d = Math.abs(i - pos);
                return (
                  <div
                    key={item}
                    style={{
                      height: 72,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 14,
                      fontSize: interpolate(
                        Math.min(1, d / 2),
                        [0, 1],
                        [38, 30],
                        clamp,
                      ),
                      fontWeight: 720,
                      color: d < 0.5 ? C.brand : d < 1.5 ? C.text : C.muted,
                      opacity:
                        d <= 1
                          ? interpolate(d, [0, 1], [1, 0.55], clamp)
                          : interpolate(
                              Math.min(2, d),
                              [1, 2],
                              [0.55, 0.16],
                              clamp,
                            ),
                    }}
                  >
                    <span style={{ opacity: Math.max(0, 1 - d * 1.6) }}>✓</span>
                    {item}
                  </div>
                );
              })}
            </div>
            <div
              style={{
                position: "absolute",
                inset: 0,
                background:
                  "linear-gradient(180deg,#080d14 0%,transparent 28%,transparent 72%,#080d14 100%)",
              }}
            />
          </div>
        </div>
      </div>
      <Caption eyebrow="FLEXIBLE & FAIR">
        <span style={{ color: C.brand }}>成本价使用。</span>{" "}
        按次、按天，灵活选择。
      </Caption>
    </Background>
  );
};

const reviewStops = [
  {
    label: "问题",
    sub: "听懂重点",
    src: "textures/live-conversation-monitor.png",
  },
  { label: "回答", sub: "查看依据", src: "textures/live-answer-workspace.png" },
  { label: "建议", sub: "找到改进", src: "textures/review-review-summary.png" },
  {
    label: "下一场",
    sub: "更有准备",
    src: "textures/review-review-timeline.png",
  },
] as const;
const reviewCamX = (f: number) => {
  const t = interpolate(f, [12, 104], [0, 1], clamp);
  return (
    interpolate(t, [0, 0.15, 0.88, 1], [0, 0.055, 0.9, 1], {
      ...clamp,
      easing: Easing.inOut(Easing.quad),
    }) * 3600
  );
};
const reviewPopFrame = (i: number) => [12, 48, 76, 98][i] - 6;
const ReviewScene: React.FC = () => {
  const f = useCurrentFrame();
  const camX = reviewCamX(f);
  const zoom = interpolate(f, [104, 114], [1, 1.22], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  return (
    <Background>
      <ProductPage
        src="textures/review-full.png"
        scale={1.02}
        blur={3}
        dim={0.72}
      />
      <div
        style={{
          position: "absolute",
          inset: 0,
          transform: `scale(${zoom})`,
          transformOrigin: "50% 63%",
        }}
      >
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            width: 5600,
            height: 1080,
            transform: `translateX(${-camX}px)`,
          }}
        >
          <div
            style={{
              position: "absolute",
              left: 420,
              top: 660,
              width: 5000,
              height: 5,
              background: "#243142",
              borderRadius: 4,
            }}
          />
          {Array.from({ length: 24 }, (_, i) => (
            <i
              key={i}
              style={{
                position: "absolute",
                left: 820 + i * 200,
                top: 649,
                width: 4,
                height: 26,
                borderRadius: 4,
                background: "#334357",
              }}
            />
          ))}
          {reviewStops.map((stop, i) => {
            const x = 960 + i * 1200;
            const p = spring({
              frame: f - reviewPopFrame(i),
              fps: 30,
              config: { damping: 11, stiffness: 160, mass: 0.9 },
              durationInFrames: 26,
            });
            return (
              <div
                key={stop.label}
                style={{ position: "absolute", left: x, top: 0 }}
              >
                <div
                  style={{
                    position: "absolute",
                    left: -3,
                    top: 620,
                    width: 6,
                    height: 84,
                    borderRadius: 4,
                    background: C.brand,
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    left: -110,
                    top: 720,
                    width: 220,
                    textAlign: "center",
                    fontSize: 36,
                    fontWeight: 800,
                  }}
                >
                  {stop.label}
                </div>
                {f >= reviewPopFrame(i) ? (
                  <div
                    style={{
                      position: "absolute",
                      left: -235,
                      top: 260,
                      width: 470,
                      height: 320,
                      border: `1px solid ${C.line}`,
                      borderRadius: 22,
                      overflow: "hidden",
                      background: C.surface,
                      boxShadow: "0 30px 80px rgba(0,0,0,.5)",
                      transform: `scaleY(${p}) scaleX(${0.64 + 0.36 * p})`,
                      transformOrigin: "50% 100%",
                      opacity: Math.min(1, p * 2),
                    }}
                  >
                    {i === 3 ? (
                      <div
                        style={{
                          position: "absolute",
                          inset: 0,
                          padding: "34px 36px",
                          background: "linear-gradient(145deg,#121c29,#091019)",
                          display: "flex",
                          flexDirection: "column",
                          gap: 18,
                        }}
                      >
                        <div
                          style={{
                            fontFamily: MONO,
                            fontSize: 28,
                            color: C.brand,
                            letterSpacing: ".1em",
                          }}
                        >
                          REVIEW COMPLETE
                        </div>
                        <div style={{ fontSize: 40, fontWeight: 800 }}>
                          复盘完成
                        </div>
                        <div
                          style={{
                            display: "grid",
                            gap: 12,
                            fontSize: 30,
                            color: "#c4cfda",
                          }}
                        >
                          {[
                            "问题记录完整",
                            "回答依据可回看",
                            "下一场行动已整理",
                          ].map((x) => (
                            <div
                              key={x}
                              style={{
                                display: "flex",
                                gap: 12,
                                alignItems: "center",
                              }}
                            >
                              <span style={{ color: C.brand }}>✓</span>
                              {x}
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <Img
                        src={staticFile(stop.src)}
                        style={{
                          width: "100%",
                          height: "100%",
                          objectFit: "cover",
                        }}
                      />
                    )}
                    {i !== 3 ? (
                      <div
                        style={{
                          position: "absolute",
                          left: 0,
                          right: 0,
                          bottom: 0,
                          padding: "20px 24px",
                          background:
                            "linear-gradient(transparent,rgba(5,9,14,.95))",
                          fontSize: 32,
                          fontWeight: 740,
                        }}
                      >
                        {stop.sub}
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      </div>
      <Caption eyebrow="INTERVIEW REVIEW">结束以后，关键节点随时回看。</Caption>
    </Background>
  );
};

const steadyValues = [
  {
    n: "01 / PRICE",
    title: "价格稳",
    body: "成本价使用\n按次 / 按天，灵活选择",
  },
  {
    n: "02 / ANSWER",
    title: "回答稳",
    body: "基于简历、JD 与知识库\n回答真实，来源可核对",
  },
  {
    n: "03 / INTERVIEW",
    title: "面试更稳",
    body: "现场辅助、截图题与复盘\n关键环节更有准备",
  },
] as const;
const OutroScene: React.FC = () => {
  const f = useCurrentFrame();
  const bars = Array.from({ length: 16 }, (_, i) => ({
    i,
    dist: Math.abs(i - 7.5) / 7.5,
    height: interpolate(i, [0, 15], [104, 42]),
  }));
  const cardsIn = interpolate(f, [72, 176], [0, 1], clamp);
  const finalIn = interpolate(f, [164, 206], [0, 1], {
    ...clamp,
    easing: ease,
  });
  const dust = Array.from({ length: 24 }, (_, i) => ({
    x: (i * 439 + 137) % 1920,
    y: (i * 613 + 271) % 1080,
    s: 2 + (i % 3),
    o: 0.1 + (i % 5) * 0.035,
  }));
  return (
    <Background>
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(900px 560px at 50% 55%,rgba(86,230,177,.18),transparent 72%)",
        }}
      />
      <div
        style={{
          position: "absolute",
          left: 120,
          right: 120,
          top: 70,
          height: 160,
          opacity: 1 - finalIn * 0.25,
        }}
      >
        {bars.map(({ i, dist, height }) => {
          const delay = i * 2.2;
          const entry = interpolate(f, [8 + delay, 42 + delay], [0, 1], {
            ...clamp,
            easing: Easing.out(Easing.cubic),
          });
          const wave = interpolate(
            f,
            [52 + dist * 10, 76 + dist * 10, 96 + dist * 10],
            [0, 1, 0],
            clamp,
          );
          return (
            <i
              key={i}
              style={{
                position: "absolute",
                left: `${i * 6.25}%`,
                bottom: 0,
                width: "3.8%",
                height,
                display: "block",
                borderRadius: 8,
                opacity: entry * (1 - finalIn * 0.75),
                background: `linear-gradient(180deg,rgba(168,245,217,${0.92 - wave * 0.1}),rgba(86,230,177,.32))`,
                boxShadow: `0 0 ${18 + wave * 24}px rgba(86,230,177,${0.12 + wave * 0.18})`,
                transform: `translateY(${(1 - entry) * (22 + dist * 34)}px) scaleY(${entry * (1 + wave * (0.08 + (1 - dist) * 0.28))})`,
                transformOrigin: "50% 100%",
                filter: `blur(${(1 - entry) * (2 + dist * 6)}px)`,
              }}
            />
          );
        })}
      </div>
      <div
        style={{
          position: "absolute",
          left: 105,
          right: 105,
          top: 240,
          display: "grid",
          gridTemplateColumns: "repeat(3,1fr)",
          gap: 24,
          opacity: cardsIn,
        }}
      >
        {steadyValues.map((item, i) => {
          const cue = 84 + i * 24;
          const t = interpolate(f, [cue, cue + 24], [0, 1], {
            ...clamp,
            easing: land,
          });
          return (
            <article
              key={item.title}
              style={{
                height: 360,
                padding: "38px 36px",
                borderRadius: 28,
                border: `1px solid ${C.line}`,
                background:
                  "linear-gradient(145deg,rgba(24,35,47,.96),rgba(10,16,23,.86))",
                boxShadow: "0 28px 80px rgba(0,0,0,.38)",
                opacity: t,
                transform: `translateY(${46 * (1 - t)}px) scale(${0.96 + 0.04 * t})`,
              }}
            >
              <div
                style={{
                  fontFamily: MONO,
                  color: C.brand,
                  fontSize: 32,
                  letterSpacing: ".11em",
                }}
              >
                {item.n}
              </div>
              <h2
                style={{
                  fontSize: 64,
                  letterSpacing: "-.05em",
                  margin: "54px 0 22px",
                }}
              >
                {item.title}
              </h2>
              <p
                style={{
                  whiteSpace: "pre-line",
                  fontSize: 32,
                  lineHeight: 1.55,
                  color: "#b8c5d2",
                  margin: 0,
                }}
              >
                {item.body}
              </p>
            </article>
          );
        })}
      </div>
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 98,
          textAlign: "center",
          opacity: finalIn,
          transform: `translateY(${28 * (1 - finalIn)}px)`,
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            gap: 20,
            marginBottom: 25,
          }}
        >
          <Img
            src={staticFile("brand/app-icon.png")}
            style={{ width: 82, height: 82, borderRadius: 22 }}
          />
          <b style={{ fontSize: 48 }}>面试稳</b>
        </div>
        <div
          style={{ fontSize: 70, fontWeight: 850, letterSpacing: "-.055em" }}
        >
          面试就选面试稳。
          <span style={{ color: C.brand }}>价格稳，回答稳，面试更稳。</span>
        </div>
      </div>
      {dust.map((d, i) => (
        <i
          key={i}
          style={{
            position: "absolute",
            left: d.x + Math.sin(f * 0.018 + i) * 12,
            top: (((d.y - f * (0.22 + (i % 4) * 0.06)) % 1080) + 1080) % 1080,
            width: d.s,
            height: d.s,
            borderRadius: 9,
            background: C.brand,
            opacity: d.o * interpolate(f, [120, 175], [0, 1], clamp),
          }}
        />
      ))}
    </Background>
  );
};

type PromoProps = { bgm?: boolean; voice?: boolean };
const OUTPUT_AUDIO_OFFSET_F = 1.28;
const PEAK_F: Record<string, number> = { "impact-deep-whoosh.mp3": 2 };
const sfxFrom = (target: number, src: string) =>
  Math.max(0, Math.round(target - (PEAK_F[src] ?? 0) - OUTPUT_AUDIO_OFFSET_F));
const SFX = [
  {
    from: sfxFrom(SHOTS.brand.from + 18, "transition-soft.mp3"),
    src: "transition-soft.mp3",
    volume: 0.28,
    duration: 42,
  },
  {
    from: sfxFrom(SHOTS.brand.from + 58, "whoosh-fast.mp3"),
    src: "whoosh-fast.mp3",
    volume: 0.28,
    duration: 52,
  },
  {
    from: sfxFrom(SHOTS.listen.from + 176, "click-camera.mp3"),
    src: "click-camera.mp3",
    volume: 0.34,
    duration: 16,
  },
  {
    from: sfxFrom(SHOTS.context.from + 38, "whoosh-big.mp3"),
    src: "whoosh-big.mp3",
    volume: 0.32,
    duration: 68,
  },
  {
    from: sfxFrom(SHOTS.context.from + 116, "transition-soft.mp3"),
    src: "transition-soft.mp3",
    volume: 0.25,
    duration: 42,
  },
  {
    from: sfxFrom(SHOTS.answer.from + 30, "transition-soft.mp3"),
    src: "transition-soft.mp3",
    volume: 0.25,
    duration: 42,
  },
  {
    from: sfxFrom(SHOTS.answer.from + 184, "click-camera.mp3"),
    src: "click-camera.mp3",
    volume: 0.32,
    duration: 16,
  },
  {
    from: sfxFrom(SHOTS.screenshot.from + 16, "data-scan.mp3"),
    src: "data-scan.mp3",
    volume: 0.32,
    duration: 88,
  },
  {
    from: sfxFrom(SHOTS.pricing.from + 146, "click-camera.mp3"),
    src: "click-camera.mp3",
    volume: 0.3,
    duration: 16,
  },
  {
    from: sfxFrom(SHOTS.review.from + 12, "whoosh-fast.mp3"),
    src: "whoosh-fast.mp3",
    volume: 0.29,
    duration: 52,
  },
  {
    from: sfxFrom(SHOTS.review.from + 104, "impact-deep-whoosh.mp3"),
    src: "impact-deep-whoosh.mp3",
    volume: 0.3,
    duration: 46,
  },
  {
    from: sfxFrom(SHOTS.outro.from + 6, "riser-cine.mp3"),
    src: "riser-cine.mp3",
    volume: 0.34,
    duration: 110,
  },
  {
    from: sfxFrom(SHOTS.outro.from + 128, "impact-deep-whoosh.mp3"),
    src: "impact-deep-whoosh.mp3",
    volume: 0.5,
    duration: 100,
  },
  {
    from: sfxFrom(SHOTS.outro.from + 176, "sparkle.mp3"),
    src: "sparkle.mp3",
    volume: 0.31,
    duration: 96,
  },
] as const;

const VOICE = [
  { target: 8, duration: 165, src: "voice-01.mp3" },
  { target: 178, duration: 144, src: "voice-02.mp3" },
  { target: 402, duration: 174, src: "voice-03.mp3" },
  { target: 615, duration: 186, src: "voice-04.mp3" },
  { target: 882, duration: 162, src: "voice-05.mp3" },
  { target: 1089, duration: 201, src: "voice-06.mp3" },
  { target: 1294, duration: 156, src: "voice-07.mp3" },
  { target: 1462, duration: 147, src: "voice-08.mp3" },
  { target: 1626, duration: 147, src: "voice-09.mp3" },
] as const;

const voiceFrom = (target: number) =>
  Math.max(0, Math.round(target - OUTPUT_AUDIO_OFFSET_F));

export const OfferSteadyPromo: React.FC<PromoProps> = ({
  bgm = true,
  voice = false,
}) => {
  const f = useCurrentFrame();
  const voiceDuck = voice
    ? VOICE.reduce((level, item) => {
        const start = voiceFrom(item.target);
        const envelope = interpolate(
          f,
          [
            start - 8,
            start + 4,
            start + item.duration - 8,
            start + item.duration + 8,
          ],
          [1, 0.36, 0.36, 1],
          clamp,
        );
        return Math.min(level, envelope);
      }, 1)
    : 1;
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Sequence from={SHOTS.brand.from} durationInFrames={SHOTS.brand.duration}>
        <SceneMotion duration={SHOTS.brand.duration} outKind="B">
          <BrandScene />
        </SceneMotion>
      </Sequence>
      <Sequence
        from={SHOTS.listen.from}
        durationInFrames={SHOTS.listen.duration}
      >
        <SceneMotion duration={SHOTS.listen.duration} inKind="B" outKind="C">
          <ListenScene />
        </SceneMotion>
      </Sequence>
      <Sequence
        from={SHOTS.context.from}
        durationInFrames={SHOTS.context.duration}
      >
        <SceneMotion duration={SHOTS.context.duration} inKind="C" outKind="C">
          <ContextScene />
        </SceneMotion>
      </Sequence>
      <Sequence
        from={SHOTS.answer.from}
        durationInFrames={SHOTS.answer.duration}
      >
        <SceneMotion duration={SHOTS.answer.duration} inKind="C" outKind="A">
          <AnswerScene />
        </SceneMotion>
      </Sequence>
      <Sequence
        from={SHOTS.screenshot.from}
        durationInFrames={SHOTS.screenshot.duration}
      >
        <SceneMotion
          duration={SHOTS.screenshot.duration}
          inKind="A"
          outKind="C"
        >
          <ScreenshotScene />
        </SceneMotion>
      </Sequence>
      <Sequence
        from={SHOTS.pricing.from}
        durationInFrames={SHOTS.pricing.duration}
      >
        <SceneMotion duration={SHOTS.pricing.duration} inKind="C" outKind="C">
          <PricingScene />
        </SceneMotion>
      </Sequence>
      <Sequence
        from={SHOTS.review.from}
        durationInFrames={SHOTS.review.duration}
      >
        <SceneMotion duration={SHOTS.review.duration} inKind="C" outKind="B">
          <ReviewScene />
        </SceneMotion>
      </Sequence>
      <Sequence from={SHOTS.outro.from} durationInFrames={SHOTS.outro.duration}>
        <SceneMotion duration={SHOTS.outro.duration} inKind="B">
          <OutroScene />
        </SceneMotion>
      </Sequence>
      {(
        [
          { cue: SHOTS.listen.from, kind: "B" },
          { cue: SHOTS.context.from, kind: "C" },
          { cue: SHOTS.answer.from, kind: "C" },
          { cue: SHOTS.screenshot.from, kind: "A" },
          { cue: SHOTS.pricing.from, kind: "C" },
          { cue: SHOTS.review.from, kind: "C" },
          { cue: SHOTS.outro.from, kind: "B" },
        ] as const
      ).map(({ cue, kind }) => (
        <Sequence key={cue} from={cue - 6} durationInFrames={12}>
          <Transition kind={kind} />
        </Sequence>
      ))}
      {bgm ? (
        <Audio
          src={staticFile("audio/bgm.mp3")}
          volume={interpolate(
            f,
            [0, 30, 1740, 1800],
            [0, 0.23 * voiceDuck, 0.23 * voiceDuck, 0],
            clamp,
          )}
        />
      ) : null}
      {SFX.map((s, i) => (
        <Sequence
          key={`${s.src}-${i}`}
          from={s.from}
          durationInFrames={s.duration}
        >
          <Audio src={staticFile(`audio/${s.src}`)} volume={s.volume} />
        </Sequence>
      ))}
      {voice
        ? VOICE.map((item) => (
            <Sequence
              key={item.src}
              from={voiceFrom(item.target)}
              durationInFrames={item.duration}
            >
              <Audio src={staticFile(`audio/voice/${item.src}`)} volume={1} />
            </Sequence>
          ))
        : null}
    </AbsoluteFill>
  );
};
