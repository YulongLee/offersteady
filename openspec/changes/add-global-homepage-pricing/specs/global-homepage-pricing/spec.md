## ADDED Requirements

### Requirement: Homepage shows canonical Global pricing
The Global homepage SHALL show the current Free allowance and the current Interview Day Pass, Pro Weekly, Pro Monthly, and Job Hunt prices and terms from the canonical public Pricing catalogue.

#### Scenario: Visitor reviews homepage pricing
- **WHEN** a visitor reaches the homepage pricing section
- **THEN** the visitor sees `$0`, `$9.99 / 24 hours`, `$49.99 / 7 days`, `$99.99 / month`, and `$199.99 / 90 days` associated with their correct plan names

### Requirement: Pricing remains consistent across public surfaces
The homepage pricing section MUST consume the same plan records used by the public Pricing page rather than maintain a separate price list.

#### Scenario: A canonical public plan changes
- **WHEN** a plan name, price, term, benefit, or featured state is updated in the canonical public Pricing catalogue
- **THEN** both the homepage pricing section and public Pricing page reflect that updated record

### Requirement: Pricing presentation supports informed navigation
The homepage pricing section SHALL explain the time-based choice in concise English and provide navigation to the free start path and full Pricing page without directly initiating checkout.

#### Scenario: Visitor wants to continue
- **WHEN** a visitor selects Start free or Compare all plans
- **THEN** the site navigates to `/login` or `/pricing` respectively and does not create a payment request from the homepage

### Requirement: Pricing section is responsive and accessible
The pricing section SHALL preserve readable plan names, prices, terms, benefits, featured status, and actions across desktop and mobile layouts.

#### Scenario: Visitor uses a narrow screen
- **WHEN** the homepage is displayed at mobile width
- **THEN** pricing cards stack into a single column without horizontal overflow or clipped price information
