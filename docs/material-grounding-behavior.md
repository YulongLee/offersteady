# Material grounding behavior

OfferSteady separates interview materials into two answer-context roles.

## Fixed context: Resume and JD

Resume and JD documents are loaded from the confirmed session material snapshot before answer generation. They are inserted into the prompt as fixed context and are not counted as RAG retrieval chunks.

If an answer uses only Resume or JD, the retrieval count can be zero while `materialProvenance.fixedSourceCount` is greater than zero. This means the answer used fixed materials even though Knowledge RAG did not retrieve chunks.

## Retrieved context: Knowledge materials

Knowledge documents are the default RAG source. They are retrieved only from the confirmed session material snapshot by query embedding, vector search and rerank. They appear in provenance with `contextRole: "retrieved"` and contribute to `retrievedSourceCount`.

## No material context

When no confirmed material is available, answer tasks return `materialContextStatus: "no-context"` and `materialProvenance.noPersonalMaterialUsed: true`. Candidate-specific company names, projects, metrics and responsibilities must not be fabricated in this state.

## Degraded material context

When a selected fixed material cannot be loaded from processed artifacts, the answer task returns `materialContextStatus: "degraded"` and includes the source in `unavailableSources`. The answer must not claim that unavailable source was used.
