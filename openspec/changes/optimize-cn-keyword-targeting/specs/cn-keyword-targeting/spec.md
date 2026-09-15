## ADDED Requirements

### Requirement: Clear keyword ownership

Public pages SHALL assign the ten target keywords to one primary intent page: homepage for broad product terms, realtime page for realtime terms, technical assistant page for programmer terms, and pricing page for price terms.

#### Scenario: Broad product query
- **WHEN** a crawler reads the homepage
- **THEN** it can identify the product as an AI interview assistant without encountering a keyword list or a competing primary page declaration

#### Scenario: Realtime query
- **WHEN** a crawler reads `/features/realtime-interview`
- **THEN** the page explicitly explains realtime interview support and AI realtime answer suggestions in its title, heading, and opening content

#### Scenario: Programmer query
- **WHEN** a crawler reads `/features/ai-interview-assistant`
- **THEN** the page explicitly identifies programmer and technical interview assistance and links to relevant technical topics

#### Scenario: Price query
- **WHEN** a crawler reads `/pricing`
- **THEN** the page identifies the AI interview assistant pricing intent and explains membership, credits, and authoritative current pricing without stale hardcoded amounts

### Requirement: GEO-readable product answers

Public HTML and machine-readable product facts SHALL provide concise, factual answers to what the product is, how realtime assistance works, who the technical mode is for, and how pricing is determined.

#### Scenario: Direct answer extraction
- **WHEN** an answer engine reads the initial HTML or `llms-full.txt`
- **THEN** it can extract a direct answer and official URL for each of the four questions without relying on client-side interaction

### Requirement: Internal link coherence

The homepage and relevant public pages SHALL link to the realtime, technical assistant, and pricing pages using descriptive anchors, while supporting topic pages link back to their owning feature page.

#### Scenario: Topic cluster navigation
- **WHEN** a user or crawler follows links from the technical assistant page
- **THEN** it can reach the technical interview guide and the LLM, RAG, AI Agent, Java, frontend, and algorithms topic pages

### Requirement: Honest content boundaries

The optimization SHALL NOT claim fabricated rankings, competitor comparisons, users, accuracy, latency, awards, or guaranteed interview outcomes.

#### Scenario: Unsupported claim check
- **WHEN** SEO content is generated or reviewed
- **THEN** unsupported commercial or performance claims are absent and AI output remains described as a suggestion
