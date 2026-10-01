import { Link, Outlet } from "react-router-dom";
import { ChatCircleTextIcon, IdentificationCardIcon, ScanIcon, ClipboardTextIcon } from "@phosphor-icons/react";
import { routes } from "./routes";
import { Logo } from "./PageShell";
import { publicReviewCatalogue, publicReviewPage } from "./public-review-pages";
import { HomepageDownloads } from "./HomepageDownloads";
import { HomepageLanguages } from "./HomepageLanguages";
import { HomepageAdvantages } from "./HomepageAdvantages";
import homeCopy from "./homepage-commercial.json";
import { DeferredVideo } from "./DeferredVideo";

export function PublicLayout({ authenticated = false }: { readonly authenticated?: boolean }) {
  return (
    <div className="public-shell">
      <header className="public-nav">
        <Link to={routes.landing} aria-label="OfferSteady home"><Logo compact /></Link>
        <nav aria-label="Public navigation"><a href="/features">Features</a><a href="/#product-tour">How it works</a><a href="/pricing">Pricing</a><a href="/download">Download</a><Link className="button ghost" to={authenticated ? routes.app : routes.login}>{authenticated ? "Open workspace" : "Sign in"}</Link></nav>
      </header>
      <Outlet />
    </div>
  );
}

export function LandingPage() {
  const pricingPlans = publicReviewPage("pricing")?.plans ?? [];
  const freePlan = pricingPlans.find(plan => plan.name === "Free");
  const paidPlans = pricingPlans.filter(plan => plan.name !== "Free");
  const benefitIcons = [ChatCircleTextIcon, IdentificationCardIcon, ScanIcon, ClipboardTextIcon];
  return <main className="commercial-home">
    <section className="landing-hero">
      <div>
        <span className="kicker">YOUR AI INTERVIEW ASSISTANT</span>
        <h1>{publicReviewCatalogue.heroTitle}</h1>
        <p>{publicReviewCatalogue.productDescription}</p>
        <div className="hero-actions"><Link className="button primary large" to={routes.login}>Start free <span>→</span></Link><a className="text-link" href="#product-tour">See how it works <span aria-hidden="true">↗</span></a></div>
        <HomepageDownloads />
        <p className="hero-guidance-note">{publicReviewCatalogue.guidanceNotice}</p>
      </div>
      <div className="answer-demo" aria-label="Live answer preview">
        <div className="demo-top"><span><i className="online-dot" /> Interview guidance</span><span>Product preview</span></div>
        <small>Current question</small><h2>Tell me about a challenging project you led.</h2>
        <div className="demo-answer"><span className="advice-label">A place to start</span><ol><li>Set the context and goal in one sentence.</li><li>Focus on your decisions, actions, and trade-offs.</li><li>Close with a result you can verify.</li></ol><div className="source-pills"><span>Resume</span><span>Job description</span><span>Your experience</span></div></div>
      </div>
    </section>
    <HomepageLanguages />
    <section id="benefits" className="public-section" aria-labelledby="commercial-benefits-title">
      <div className="section-intro"><span className="kicker">BUILT FOR THE CONVERSATION</span><h2 id="commercial-benefits-title">{homeCopy.benefitsTitle}</h2><p>{homeCopy.benefitsIntro}</p></div>
      <div className="commercial-benefits">{homeCopy.benefits.map((benefit, index) => {
        const Icon = benefitIcons[index] ?? ChatCircleTextIcon;
        return <article key={benefit.label}><span><Icon size={28} weight="duotone" /></span><small>{benefit.label}</small><h3>{benefit.title}</h3><p>{benefit.body}</p></article>;
      })}</div>
    </section>
    {freePlan && paidPlans.length ? <section id="plans" className="public-section homepage-pricing" aria-labelledby="homepage-pricing-title">
      <div className="homepage-pricing-heading"><div><span className="kicker">YOUR SCHEDULE. YOUR PLAN.</span><h2 id="homepage-pricing-title">Pay for the time you need.</h2></div><p>{homeCopy.pricingIntro}</p></div>
      <article className="homepage-free-plan">
        <div><span>TRY IT FIRST</span><h3>{freePlan.name}</h3><p>{freePlan.description}</p></div>
        <div className="homepage-free-price"><strong>{freePlan.price}</strong><span>No credit card required</span></div>
        <ul>{freePlan.features.slice(0, 2).map(feature => <li key={feature}>✓ {feature}</li>)}</ul>
        <Link className="button primary" to={routes.login}>Start free <span>→</span></Link>
      </article>
      <div className="homepage-plan-grid" aria-label="OfferSteady paid plans">
        {paidPlans.map(plan => <article key={plan.name} className={`homepage-plan-card${plan.featured ? " featured" : ""}`}>
          <div className="homepage-plan-topline"><span>{plan.featured ? "WEEKLY ACCESS" : plan.name === "Pro Monthly" ? "MONTHLY SUBSCRIPTION" : "ONE-TIME PASS"}</span></div>
          <h3>{plan.name}</h3><p>{plan.description}</p>
          <div className="homepage-plan-price"><strong>{plan.price}</strong><span>{plan.term}</span></div>
          <ul>{plan.features.map(feature => <li key={feature}>✓ {feature}</li>)}</ul>
          <div className="plan-delivery"><p>{plan.billing}</p></div>
        </article>)}
      </div>
      <div className="commercial-plan-note"><p>{homeCopy.accessNote}</p><p>{homeCopy.checkoutNote}</p></div>
      <div className="homepage-pricing-actions"><Link className="button primary large" to={routes.pricing}>Compare all plans <span>→</span></Link><p>See full allowances, access periods and <Link to={routes.refundPolicy}>refund details</Link> before you choose.</p></div>
    </section> : null}
    <section id="product-tour" className="public-section" aria-labelledby="commercial-tour-title">
      <div className="section-intro"><span className="kicker">HOW IT WORKS</span><h2 id="commercial-tour-title">{homeCopy.tourTitle}</h2></div>
      <div className="commercial-steps">{homeCopy.steps.map((step, index) => <article key={step.title}><b>0{index + 1}</b><h3>{step.title}</h3><p>{step.body}</p></article>)}</div>
      <div className="commercial-videos">{homeCopy.videos.map(video => <article key={video.id}>
        <DeferredVideo label={video.label} poster={video.poster} src={video.src} />
        <h3 id={video.id}>{video.title}</h3><p>{video.description}</p>
      </article>)}</div>
    </section>
    <HomepageAdvantages compact />
    <section id="faq" className="public-section commercial-faq-layout" aria-labelledby="commercial-faq-title">
      <div className="section-intro"><span className="kicker">BEFORE YOU START</span><h2 id="commercial-faq-title">A few things worth knowing.</h2><p>Still have a question? <Link className="text-link" to={routes.contact}>Talk to us</Link></p></div>
      <div className="commercial-faq-list">{homeCopy.faqs.map(faq => <details key={faq.question}><summary>{faq.question}</summary><p>{faq.answer}</p><Link to={faq.href}>{faq.linkLabel} →</Link></details>)}</div>
    </section>
    <section className="commercial-closing" aria-labelledby="commercial-closing-title"><div><h2 id="commercial-closing-title">{homeCopy.closingTitle}</h2><p>{homeCopy.closingBody}</p></div><Link className="button primary large" to={routes.login}>Start free <span>→</span></Link></section>
    <footer className="public-footer">
      <div className="public-footer-main"><section className="footer-brand"><Logo compact /><p>AI interview guidance for preparation, live sessions, written assessments, and review.</p><span>Always verify suggestions and answer from your real experience.</span></section><nav className="footer-column"><h2>Product</h2><Link to={routes.features}>Features</Link><Link to={routes.interviewQuestions}>Interview topics</Link><Link to={routes.guides}>Guides</Link><Link to={routes.pricing}>Pricing</Link><Link to={routes.download}>Download</Link><Link to={routes.login}>Sign in</Link></nav><nav className="footer-column"><h2>Company &amp; legal</h2><Link to={routes.about}>About</Link><Link to={routes.contact}>Contact</Link><Link to={routes.security}>Security</Link><Link to={routes.terms}>Terms of Service</Link><Link to={routes.privacy}>Privacy Policy</Link><Link to={routes.refundPolicy}>Refund Policy</Link></nav><section className="footer-contact"><h2>Support</h2><p><a href="mailto:contact@oneshowailab.com">contact@oneshowailab.com</a></p><p>Never send passwords, verification codes, or complete identity documents to support.</p></section></div>
      <div className="public-footer-legal"><span>© 2026 OfferSteady</span><span>Operated by {publicReviewCatalogue.operator} · {publicReviewCatalogue.operatorLocation}</span></div>
    </footer>
  </main>;
}
