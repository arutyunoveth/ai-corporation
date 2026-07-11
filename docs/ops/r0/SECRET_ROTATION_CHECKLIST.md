# Secret rotation checklist

1. If a secret is found in a working tree or historical commit, revoke it with its issuer first.
2. Replace it in the local `0600` environment file or secret manager; do not add it to GitHub Actions or Markdown.
3. Verify logs, deploy archives, and test fixtures contain no value.
4. Record only the variable name, revocation date, and owner in the incident record.
5. Do not rewrite history automatically during R0; coordinate a separate rotation/remediation change if required.
