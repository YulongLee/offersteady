const escape = value => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");

// Pure static presentation: same content records as React, no runtime requests.
export function renderCommercialHomepage({ catalogue, home, downloadsHtml }) {
  const plans = catalogue.pages.find(page => page.slug === "pricing").plans;
  const benefits = home.benefits.map(item => `<article><p>${escape(item.label)}</p><h3>${escape(item.title)}</h3><p>${escape(item.body)}</p></article>`).join("");
  const pricing = plans.map(plan => `<article><h3>${escape(plan.name)}</h3><p>${escape(plan.price + plan.term)}</p><p>${escape(plan.description)}</p><ul>${plan.features.map(feature => `<li>${escape(feature)}</li>`).join("")}</ul><p>${escape(plan.billing)}</p><p>${escape(plan.accessStarts)}</p></article>`).join("");
  const steps = home.steps.map(step => `<li><strong>${escape(step.title)}</strong><p>${escape(step.body)}</p></li>`).join("");
  const videos = home.videos.map(video => `<article><h3>${escape(video.title)}</h3><p>${escape(video.description)}</p><video aria-label="${escape(video.label)}" controls muted playsinline preload="metadata" poster="${escape(video.poster)}" style="width:100%;aspect-ratio:16/9"><source src="${escape(video.src)}" type="video/mp4"></video></article>`).join("");
  const faqs = home.faqs.map(faq => `<details><summary>${escape(faq.question)}</summary><p>${escape(faq.answer)}</p><a href="${escape(faq.href)}">${escape(faq.linkLabel)}</a></details>`).join("");
  return `<main class="seo-prerender">
<header><p>OfferSteady · AI Interview Assistant</p><h1>${escape(catalogue.heroTitle)}</h1><p>${escape(catalogue.productDescription)}</p><nav><a href="/login">Start free</a><a href="#product-tour">See how it works</a></nav>${downloadsHtml}<p>${escape(catalogue.guidanceNotice)}</p><nav aria-label="Public navigation"><a href="/features">Features</a><a href="/pricing">Pricing</a><a href="/download">Download</a></nav></header>
<section id="benefits"><h2>${escape(home.benefitsTitle)}</h2><p>${escape(home.benefitsIntro)}</p>${benefits}</section>
<section id="plans"><h2>Pay for the time you need.</h2><p>${escape(home.pricingIntro)}</p>${pricing}<p>${escape(home.accessNote)}</p><p>${escape(home.checkoutNote)}</p><nav><a href="/login">Start free</a><a href="/pricing">Compare all plans</a><a href="/refund-policy">Refund Policy</a></nav></section>
<section id="product-tour"><h2>${escape(home.tourTitle)}</h2><ol>${steps}</ol>${videos}</section>
<section id="faq"><h2>A few things worth knowing.</h2>${faqs}</section>
<section><h2>${escape(home.closingTitle)}</h2><p>${escape(home.closingBody)}</p><a href="/login">Start free</a></section>
<footer><p>© 2026 OfferSteady</p><p>Operated by ${escape(catalogue.operator)} · ${escape(catalogue.operatorLocation)}</p><p>Support: <a href="mailto:${escape(catalogue.supportEmail)}">${escape(catalogue.supportEmail)}</a></p><nav><a href="/features">Features</a><a href="/interview-questions">Interview topics</a><a href="/guides">Guides</a><a href="/pricing">Pricing</a><a href="/download">Download</a><a href="/security">Security</a><a href="/about">About</a><a href="/contact">Contact</a><a href="/terms">Terms of Service</a><a href="/privacy">Privacy Policy</a><a href="/refund-policy">Refund Policy</a></nav></footer>
</main>`;
}
