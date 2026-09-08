import { useEffect, useRef, useState } from "react";
import { ArrowLeftIcon, ArrowRightIcon, PauseIcon, PlayIcon, QuotesIcon, UserIcon } from "@phosphor-icons/react";
import feedback from "./homepage-feedback.json";
import "./homepage-feedback.css";

export function HomepageFeedback() {
  const section = useRef<HTMLElement>(null);
  const touchStart = useRef<{ x: number; y: number } | null>(null);
  const pointerPlayIntent = useRef<boolean | null>(null);
  const [index, setIndex] = useState(0);
  const [count, setCount] = useState(3);
  const [playing, setPlaying] = useState(false);
  const [hovered, setHovered] = useState(false);
  const [inView, setInView] = useState(false);
  const [pageVisible, setPageVisible] = useState(true);
  const total = feedback.entries.length;

  useEffect(() => {
    if (!window.matchMedia) return;
    const mobile = window.matchMedia("(max-width: 720px)");
    const tablet = window.matchMedia("(max-width: 1050px)");
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    const resize = () => setCount(mobile.matches ? 1 : tablet.matches ? 2 : 3);
    const motion = () => { if (reduced.matches) setPlaying(false); };
    resize();
    setPlaying(!reduced.matches);
    mobile.addEventListener("change", resize);
    tablet.addEventListener("change", resize);
    reduced.addEventListener("change", motion);
    return () => {
      mobile.removeEventListener("change", resize);
      tablet.removeEventListener("change", resize);
      reduced.removeEventListener("change", motion);
    };
  }, []);

  useEffect(() => {
    const visibility = () => setPageVisible(!document.hidden);
    visibility();
    document.addEventListener("visibilitychange", visibility);
    // Older browsers keep manual navigation instead of starting an unobserved timer.
    const observer = typeof IntersectionObserver === "undefined" ? null : new IntersectionObserver(
      ([entry]) => setInView(Boolean(entry?.isIntersecting)), { threshold: 0.15 },
    );
    if (section.current) observer?.observe(section.current);
    return () => { observer?.disconnect(); document.removeEventListener("visibilitychange", visibility); };
  }, []);

  const rotating = playing && !hovered && inView && pageVisible;
  useEffect(() => {
    if (!rotating) return;
    const timer = window.setInterval(() => setIndex(current => (current + 1) % total), 10_000);
    return () => window.clearInterval(timer);
  }, [rotating, total]);

  const navigate = (direction: number) => {
    setPlaying(false);
    setIndex(current => (current + direction + total) % total);
  };
  const visibleEntries = Array.from({ length: count }, (_, offset) => feedback.entries[(index + offset) % total]!);

  return <section ref={section} id="user-feedback" className="public-section homepage-feedback"
    aria-labelledby="homepage-feedback-title" aria-roledescription="carousel"
    onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)}
    onFocusCapture={() => setPlaying(false)}>
    <div className="feedback-heading">
      <div><span className="kicker">THE USER PERSPECTIVE</span><h2 id="homepage-feedback-title">{feedback.heading}<span aria-hidden="true">.</span></h2></div>
      <p>{feedback.intro}</p>
    </div>
    <div className="feedback-cards" id="homepage-feedback-cards" style={{ gridTemplateColumns: `repeat(${count}, minmax(0, 1fr))` }}
      aria-live={rotating ? "off" : "polite"} aria-atomic="true"
      onTouchStart={event => {
        setPlaying(false);
        const touch = event.touches[0];
        touchStart.current = touch ? { x: touch.clientX, y: touch.clientY } : null;
      }}
      onTouchCancel={() => { touchStart.current = null; }}
      onTouchEnd={event => {
        const touch = event.changedTouches[0];
        const start = touchStart.current;
        if (touch && start) {
          const dx = touch.clientX - start.x;
          const dy = touch.clientY - start.y;
          if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)) navigate(dx < 0 ? 1 : -1);
        }
        touchStart.current = null;
      }}>
      {visibleEntries.map(entry => <article key={entry.id} className="feedback-card" aria-roledescription="slide"
        aria-label={`Feedback ${feedback.entries.indexOf(entry) + 1} of ${total}`}>
        <div className="feedback-card-top"><span>{entry.topic}</span><QuotesIcon weight="fill" size={30} aria-hidden="true" /></div>
        <blockquote><p>{entry.quote}</p></blockquote>
        <div className="feedback-author"><span className="feedback-avatar" aria-hidden="true"><UserIcon size={19} /></span><span>Anonymous user</span></div>
      </article>)}
    </div>
    <div className="feedback-bottom">
      <p className="feedback-note">{feedback.note}</p>
      <div className="feedback-controls" role="group" aria-label="Feedback controls">
        <button type="button" className="feedback-play" aria-label={playing ? "Pause feedback rotation" : "Play feedback rotation"}
          aria-controls="homepage-feedback-cards"
          onPointerDown={() => { pointerPlayIntent.current = !playing; }}
          onPointerCancel={() => { pointerPlayIntent.current = null; }}
          onClick={() => { setPlaying(pointerPlayIntent.current ?? !playing); pointerPlayIntent.current = null; }}>
          {playing ? <PauseIcon size={16} weight="fill" aria-hidden="true" /> : <PlayIcon size={16} weight="fill" aria-hidden="true" />}
        </button>
        <span className="feedback-position" aria-label={`Starting at feedback ${index + 1} of ${total}`}><strong>{String(index + 1).padStart(2, "0")}</strong><span>/ {total}</span></span>
        <button type="button" aria-label="Previous feedback" aria-controls="homepage-feedback-cards" onClick={() => navigate(-1)}><ArrowLeftIcon size={20} aria-hidden="true" /></button>
        <button type="button" aria-label="Next feedback" aria-controls="homepage-feedback-cards" onClick={() => navigate(1)}><ArrowRightIcon size={20} aria-hidden="true" /></button>
      </div>
    </div>
  </section>;
}
