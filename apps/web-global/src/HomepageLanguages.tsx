import { INTERVIEW_LANGUAGE_REGISTRY } from "@offersteady/protocol";

const productionLanguages = INTERVIEW_LANGUAGE_REGISTRY.filter(language => language.tier === "production");

export function HomepageLanguages() {
  return <section className="public-section homepage-languages" aria-labelledby="homepage-languages-title">
    <div className="homepage-languages-copy">
      <span className="kicker">INTERVIEW IN YOUR LANGUAGE</span>
      <h2 id="homepage-languages-title">Practice in the language you will use.</h2>
      <p>Choose your interview language before you begin. Transcription, question detection and AI guidance stay aligned throughout the session.</p>
    </div>
    <div className="homepage-language-list" role="region" aria-label="Production interview languages">
      {productionLanguages.map(language => <span className="homepage-language-pill" key={language.locale}><strong>{language.label}</strong><small>{language.locale}</small></span>)}
    </div>
    <p className="homepage-languages-note">{productionLanguages.length} languages are ready for production sessions. Additional languages are available as beta options in Settings.</p>
  </section>;
}
