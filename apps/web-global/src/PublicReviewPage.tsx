import { Link } from "react-router-dom";
import { publicReviewCatalogue as catalogue, publicReviewPage } from "./public-review-pages";
import { routes } from "./routes";

function ReviewFooter() {
  return <footer className="public-footer review-footer">
    <div className="public-footer-main">
      <section className="footer-brand"><strong>OfferSteady</strong><p>Responsible AI interview guidance grounded in experience you can verify.</p><span>Follow the interview organiser's rules and applicable recording and AI-assistance requirements.</span></section>
      <nav className="footer-column" aria-label="Product pages"><h2>Product</h2><Link to={routes.features}>Features</Link><Link to={routes.interviewQuestions}>Interview topics</Link><Link to={routes.guides}>Guides</Link><Link to={routes.pricing}>Pricing</Link><Link to={routes.download}>Download</Link></nav>
      <nav className="footer-column" aria-label="Legal and company pages"><h2>Company &amp; legal</h2><Link to={routes.about}>About</Link><Link to={routes.contact}>Contact</Link><Link to={routes.security}>Security</Link><Link to={routes.terms}>Terms of Service</Link><Link to={routes.privacy}>Privacy Policy</Link><Link to={routes.refundPolicy}>Refund Policy</Link></nav>
      <section className="footer-contact"><h2>Support</h2><p><a href={`mailto:${catalogue.supportEmail}`}>{catalogue.supportEmail}</a></p><p>Operated by {catalogue.operator}<br />{catalogue.operatorLocation}</p></section>
    </div>
    <div className="public-footer-legal"><span>© 2026 OfferSteady</span></div>
  </footer>;
}

export function PublicReviewPage({ slug }: { readonly slug: string }) {
  const page = publicReviewPage(slug);
  if (!page) return null;
  const legal = ["terms", "privacy", "refund-policy"].includes(slug);
  return <main className="review-page">
    <header className="review-hero">
      <span className="kicker">{page.eyebrow}</span><h1>{page.h1}</h1><p>{page.intro}</p>
      {page.actions ? <div className="review-actions" aria-label="Page actions">{page.actions.map(action => <div key={action.href}><Link className="button primary large" to={action.href}>{action.label} <span>→</span></Link><small>{action.detail}</small></div>)}</div> : null}
      {legal ? <small>Effective date / last updated: {catalogue.updatedAt}</small> : null}
    </header>
    {page.plans ? <section className="review-pricing-grid" aria-label="OfferSteady pricing plans">{page.plans.map(plan => <article key={plan.name} className={plan.featured ? "featured" : ""}>
      {plan.featured ? <span className="review-plan-badge">Most popular</span> : null}
      <h2>{plan.name}</h2><p>{plan.description}</p>
      <div className="review-plan-price"><strong>{plan.price}</strong><span>{plan.term}</span></div>
      <ul>{plan.features.map(feature => <li key={feature}>✓ {feature}</li>)}</ul>
      <div className="plan-delivery"><p>{plan.billing}</p><p><strong>Access begins: </strong>{plan.accessStarts}</p></div>
      {plan.href ? <Link className="button primary full" to={plan.href}>{plan.action}</Link> : <button className="button ghost full" type="button" disabled>{plan.action}</button>}
    </article>)}</section> : null}
    <article className="review-document">{page.sections.map(section => <section key={section.heading}><h2>{section.heading}</h2>{section.paragraphs.map(paragraph => <p key={paragraph}>{paragraph}</p>)}</section>)}</article>
    <ReviewFooter />
  </main>;
}
