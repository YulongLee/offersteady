## ADDED Requirements

### Requirement: Local-only configuration

The tool SHALL read the provider endpoint, domain, keyword list, and one complete credential set from local environment variables or an explicitly supplied untracked env file, and SHALL never expose credentials in browser bundles, reports, logs, or command output.

#### Scenario: Missing credentials
- **WHEN** the tool starts without AccessKey/Secret or AppCode
- **THEN** it exits with a `missing_credentials` error and performs no provider request

#### Scenario: Complete local configuration
- **WHEN** a complete credential set and valid domain are provided
- **THEN** the tool accepts the configuration without printing any secret value

### Requirement: Ranking query

The tool SHALL support querying one keyword and SHALL return at most the first 50 provider results, including rank, title, and URL when supplied by the provider.

#### Scenario: Successful query
- **WHEN** a configured keyword is submitted and the provider responds successfully
- **THEN** the result contains the keyword, observed timestamp, status, and up to 50 ranked entries

#### Scenario: No matching result
- **WHEN** the provider responds successfully with no matching entry for the domain
- **THEN** the result status is `not_found` and is not represented as a numeric rank of zero

### Requirement: Batch refresh and safe failures

The tool SHALL support an explicit batch mode, bound request count and retry/timeout behavior, and SHALL distinguish authentication, timeout, quota, provider, and not-found outcomes.

#### Scenario: Batch refresh
- **WHEN** the operator explicitly runs batch mode for a list of keywords
- **THEN** each keyword is queried at most once per run plus the configured bounded retries, with no concurrent unbounded fan-out

#### Scenario: Provider failure
- **WHEN** a request times out or the provider rejects its signature
- **THEN** the tool records a safe error status and does not claim a ranking result

### Requirement: Report export for conversation analysis

The tool SHALL export JSON and Markdown reports containing the domain, keyword, observed time, status, top rank when available, matched URL/title, and the first 50 result entries, while omitting credentials and raw authorization headers.

#### Scenario: Export report
- **WHEN** a query or batch run completes
- **THEN** the operator can save a JSON and/or Markdown report suitable for sharing in the current conversation

#### Scenario: Secret redaction
- **WHEN** an exported report or error is generated
- **THEN** no AccessKey, Secret, AppCode, authorization header, or environment-variable value appears in the output

### Requirement: Production isolation

The tool SHALL run without changing production API behavior, admin permissions, website content, sitemap, or production databases.

#### Scenario: Offline development run
- **WHEN** the operator runs the tool locally
- **THEN** it contacts only the configured ranking provider and writes only the explicitly requested local report files
