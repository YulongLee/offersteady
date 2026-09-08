import { useMemo, useState } from "react";
import type { BillingSupportConfig } from "@offersteady/protocol";
import { Link, useLocation } from "react-router-dom";
import { guideContent, safeGuideContent } from "./guide-content";
import { routes } from "./routes";

export function GuidePage({ support }: { readonly support: BillingSupportConfig }) {
  const location = useLocation();
  const [query, setQuery] = useState("");
  const content = safeGuideContent(guideContent);
  const publicView = location.pathname === routes.publicGuide;
  const initial = location.hash.slice(1).split("/")[0];
  const [activeId, setActiveId] = useState(
    content.chapters.some((item) => item.id === initial) ? initial : content.chapters[0]!.id,
  );

  const matches = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return content.chapters;
    return content.chapters.filter((chapter) =>
      `${chapter.title} ${chapter.summary} ${chapter.keywords.join(" ")} ${JSON.stringify(chapter.sections)}`
        .toLowerCase()
        .includes(normalized),
    );
  }, [content.chapters, query]);

  const active = content.chapters.find((item) => item.id === activeId) ?? content.chapters[0]!;
  const index = content.chapters.indexOf(active);
  const choose = (id: string) => {
    setActiveId(id);
    window.history.replaceState({}, "", `${location.pathname}#${id}`);
  };

  return (
    <main className="app-page guide-page">
      <header className="page-header">
        <div>
          <span className="kicker">USER GUIDE · v{content.version}</span>
          <h1>User guide</h1>
          <p>Find practical guidance from first sign-in through a live interview or written exam.</p>
        </div>
        <Link className="button primary" to={publicView ? routes.login : routes.app}>
          {publicView ? "Get started" : "Back to workspace"}
        </Link>
      </header>

      <label className="guide-search">
        <span>Search the guide</span>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="For example: Windows, screenshot, microphone"
        />
      </label>

      <div className="guide-layout">
        <aside className="panel guide-toc" aria-label="User guide contents">
          {matches.length ? matches.map((chapter) => (
            <button
              key={chapter.id}
              className={chapter.id === active.id ? "active" : ""}
              onClick={() => choose(chapter.id)}
            >
              <strong>{chapter.title}</strong>
              <small>{chapter.summary}</small>
            </button>
          )) : <p>No matching guidance. Try a shorter search term.</p>}
        </aside>

        <article className="panel guide-article">
          <span className="guide-index">
            {String(index + 1).padStart(2, "0")} / {String(content.chapters.length).padStart(2, "0")}
          </span>
          <h2>{active.title}</h2>
          <p className="guide-summary">{active.summary}</p>
          {active.sections.map((section) => (
            <section id={`${active.id}/${section.id}`} key={section.id}>
              <h3>{section.title}</h3>
              {section.paragraphs.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
            </section>
          ))}
          <nav className="guide-pager" aria-label="Guide chapters">
            <button disabled={index === 0} onClick={() => choose(content.chapters[index - 1]!.id)}>
              ← Previous
            </button>
            <button
              disabled={index === content.chapters.length - 1}
              onClick={() => choose(content.chapters[index + 1]!.id)}
            >
              Next →
            </button>
          </nav>
        </article>
      </div>

      <section className="guide-support">
        <div>
          <span className="kicker">NEED MORE HELP?</span>
          <h2>Contact support</h2>
          <p>Include an order or session reference when relevant. Never send passwords or one-time codes.</p>
        </div>
        <div className="support-contacts">
          <article>
            <small>Support email</small>
            <strong>{support.email}</strong>
            <a href={`mailto:${support.email}`}>Send email</a>
          </article>
        </div>
      </section>
    </main>
  );
}
