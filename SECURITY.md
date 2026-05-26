# Security

AdLint is local-first decision-support software for reviewing ad copy, landing
pages, policies, and eval data. Please report security or privacy issues
responsibly.

## Supported versions

The `main` branch is the only supported development line before a stable
release process exists.

## Reporting a vulnerability

Use GitHub private vulnerability reporting if available, or contact the
repository owner through the GitHub profile. Do not open a public issue for
secrets, private data exposure, or exploitable vulnerabilities.

Please include:

- affected commit or version
- steps to reproduce
- impact
- whether private data, credentials, or raw submissions may be exposed
- suggested remediation, if known

## Privacy and data boundaries

- Raw ad submissions should not be persisted by default.
- Tests, docs, evals, screenshots, and examples must not include private
  customer data or real sensitive campaign copy.
- Local model integrations are decision support and should not send user data to
  hosted services without explicit opt-in.
- Landing-page URLs and excerpts are treated as untrusted input.

## Maintainer response

Maintainers will acknowledge credible reports, investigate the scope, and fix or
document mitigations before public disclosure when appropriate.
