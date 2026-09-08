import { Link } from "react-router-dom";
import { routes } from "./routes";
import { publicReviewPage } from "./public-review-pages";

type Cell = { text: string; detail?: string; supported?: boolean };
const available: Cell = { text: "Available", supported: true };
const unverified: Cell = { text: "Not verified" };
const peers = ["F*** R**** AI", "P******* AI", "L*****In AI"];

export function HomepageAdvantages({ compact = false }: { readonly compact?: boolean }) {
  const plans = publicReviewPage("pricing")?.plans ?? [];
  const day = plans.find(plan => plan.name === "Interview Day Pass");
  const week = plans.find(plan => plan.name === "Pro Weekly");
  const month = plans.find(plan => plan.name === "Pro Monthly");
  if (!day || !week || !month) return null;
  const rows: { title: string; detail: string; own: Cell; peers: Cell[] }[] = [
    { title: "Live transcription", detail: "Follow the conversation in real time", own: available, peers: [available, available, available] },
    { title: "On-demand AI answers", detail: "Guidance while you work through a question", own: { ...available, detail: "Quick Answer" }, peers: [available, available, available] },
    { title: "Screenshot assistance", detail: "Support for on-screen questions", own: available, peers: [available, available, available] },
    { title: "Resume & job context", detail: "Ground suggestions in your experience", own: available, peers: [available, { text: "Resume & documents", supported: true }, available] },
    { title: "Knowledge materials", detail: "Bring additional reference content", own: { text: "Knowledge base", supported: true }, peers: [{ text: "Supporting materials", supported: true }, { text: "Document uploads", supported: true }, { text: "Supporting materials", supported: true }] },
    { title: "Answer controls", detail: "Choose when to ask for guidance", own: { text: "Manual + auto", supported: true }, peers: [{ text: "Manual + auto", supported: true }, { text: "Manual + auto", supported: true }, { text: "Auto prompting", detail: "Manual mode not verified" }] },
    { title: "Session review", detail: "Reflect after your interview", own: available, peers: [available, available, available] },
    { title: "Desktop support", detail: "Use your preferred computer", own: { text: "Windows + macOS", supported: true }, peers: [{ text: "Windows + macOS", supported: true }, { text: "Desktop app", detail: "OS coverage not verified" }, { text: "Windows + macOS", supported: true }] },
  ];
  const content = (cell: Cell) => <><span className={cell.supported ? "peer-supported" : "peer-value"}>{cell.supported && <span aria-hidden="true">✓</span>}{cell.text}</span>{cell.detail && <small>{cell.detail}</small>}</>;
  const comparison = <>    <div className="peer-day-callout"><strong>A {day.price} option for one interview day.</strong><span>24-hour access · 180 Copilot minutes · Unlimited Screen Assist</span></div>
    <div className="peer-table-top"><span>OfferSteady & selected AI interview assistants</span><span>Reviewed Sep 7, 2026</span></div>
    <div className="advantages-scroll-hint">Swipe to compare all products <span aria-hidden="true">↔</span></div>
    <div className="advantages-scroll" role="region" aria-label="AI interview assistant comparison" tabIndex={0}>
      <table className="advantages-table peer-table">
        <caption className="advantages-sr-only">Selected AI interview assistants: plan prices, durations and advertised capabilities. Competitor names are partially masked.</caption>
        <colgroup><col style={{ width: "25%" }} /><col style={{ width: "24%" }} /><col /><col /><col /></colgroup>
        <thead><tr><th scope="col"><span className="advantages-overline">SIDE BY SIDE</span><strong>What you get</strong></th><th scope="col" className="advantages-featured"><span className="advantages-overline">BUILT FOR YOUR TIMELINE</span><strong>✦ OfferSteady</strong><small>Start with 24 hours</small></th>{peers.map(peer => <th scope="col" key={peer}><span className="advantages-overline">AI INTERVIEW ASSISTANT</span><strong>{peer}</strong><small>Name partially masked</small></th>)}</tr></thead>
        <tbody>{rows.map(row => <tr key={row.title}><th scope="row"><strong>{row.title}</strong><small>{row.detail}</small></th><td className="advantages-featured" data-product="OfferSteady">{content(row.own)}</td>{row.peers.map((cell, index) => <td key={peers[index]} data-product={peers[index]}>{content(cell)}</td>)}</tr>)}
          <tr className="peer-price-row"><th scope="row"><strong>Plans & pricing</strong><small>Selected options · USD</small></th><td className="advantages-featured" data-product="OfferSteady"><div className="peer-plan"><strong>{day.price}</strong><small>24 hours · 180 Copilot minutes</small></div><div className="peer-plan"><strong>{week.price}</strong><small>7 days · Unlimited Copilot</small></div><div className="peer-plan"><strong>{month.price}</strong><small>Per month · Unlimited Copilot</small></div></td><td data-product={peers[0]}>{content({ text: "$90.00", detail: "Per month¹" })}<small>Quarterly and annual options</small></td><td data-product={peers[1]}>{content({ text: "$78.00", detail: "Per week" })}<div className="peer-plan">{content({ text: "$149.90", detail: "Per month" })}</div><small>Credit packs also available</small></td><td data-product={peers[2]}>{content(unverified)}<small>Current numeric price</small><small>Unlimited, credits & lifetime options</small></td></tr>
        </tbody>
      </table>
    </div>
    <div className="peer-notes"><p>Selected public plans, not a market-wide ranking. USD prices before any applicable taxes. Durations, renewal terms and allowances differ; day passes, credit packs and subscriptions are not equivalent.</p><p><strong>Not listed</strong> means not found in the official listings reviewed—not confirmed unavailable. <strong>Not verified</strong> means the current value could not be confirmed. Capabilities may require a paid tier and do not imply equal performance or limits.</p><p>¹ {peers[0]} pricing is from its official pricing article dated Aug 17, 2026. Prices and offers can change. Competitor names are partially masked; source references are retained for review. No affiliation or endorsement is implied.</p></div>
</>;
  return <section id="why-offersteady" className="public-section homepage-advantages peer-comparison" aria-labelledby="advantages-title">
    <div className="advantages-heading"><div><span className="kicker">COMPARE YOUR OPTIONS</span><h2 id="advantages-title">The tools you need.<br /><span>The time you choose.</span></h2></div><p>Live guidance, Screen Assist and your own materials in one workflow. Compare the features, then choose a plan around your interview schedule.</p></div>
    {compact ? <details className="commercial-comparison"><summary>Compare features and pricing</summary>{comparison}</details> : comparison}
    <div className="advantages-bottom"><div><span className="advantages-overline">START SMALL. STAY FLEXIBLE.</span><h3>Your next interview does not need an annual plan.</h3><p>Explore the free plan first. See all OfferSteady allowances and terms before choosing.</p></div><div className="advantages-actions"><Link to={routes.login} className="button primary">Start free <span aria-hidden="true">↗</span></Link><a href="#plans">Explore plans <span aria-hidden="true">↓</span></a></div></div>
  </section>;
}
