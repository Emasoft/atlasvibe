# Security Policy

## Supported Versions

AtlasVibe is currently in active development. Security updates will be applied to:

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of AtlasVibe seriously. If you have discovered a security vulnerability, please follow these steps:

### 1. Do NOT Create a Public Issue

Security vulnerabilities should not be reported through public GitHub issues.

### 2. Email Security Report

Send an email to: 713559+Emasoft@users.noreply.github.com

Include the following information:
- Type of issue (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

### 3. Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 5 business days
- **Resolution Target**: 30-90 days depending on severity

## Security Best Practices for Contributors

### 1. Dependencies

- Always use `uv lock` to ensure reproducible builds
- Regularly update dependencies: `uv lock --upgrade`
- Check for vulnerabilities: `uv pip audit`
- Never commit `uv.lock` with known vulnerable packages

### 2. Secrets Management

- **Never commit secrets** to the repository
- Use environment variables for sensitive data
- All commits are scanned by Gitleaks
- Only the following are allowed in commits:
  - Git author: `Emasoft`
  - Git email: `713559+Emasoft@users.noreply.github.com`

### 3. Code Security

- Validate all user inputs
- Use parameterized queries for databases
- Implement proper authentication and authorization
- Follow OWASP security guidelines
- Enable CORS only for trusted origins

### 4. Pre-commit Checks

Always run pre-commit hooks before pushing:
```bash
pre-commit run --all-files
```

### 5. CI/CD Security

Our CI/CD pipeline includes:
- Secret scanning with Gitleaks
- Dependency vulnerability scanning
- Code quality and security linting
- Automated security updates via Dependabot

## Security Features

### Current Security Measures

1. **Secret Detection**
   - Gitleaks integration in pre-commit and CI/CD
   - Strict allowlist configuration
   - Automatic rejection of commits with secrets

2. **Dependency Management**
   - Using `uv` for deterministic builds
   - Weekly dependency audits
   - Automated security updates

3. **Code Quality**
   - Static analysis with Ruff and mypy
   - Type checking enforcement
   - Security-focused linting rules

4. **Access Control**
   - Branch protection on main
   - Required PR reviews
   - Automated CI checks before merge

### Planned Security Enhancements

1. **Runtime Security**
   - Sandboxed block execution
   - Resource limits for user code
   - Input validation framework

2. **Authentication**
   - OAuth2/OIDC support
   - API key management
   - Role-based access control

3. **Audit Logging**
   - Comprehensive activity logging
   - Security event monitoring
   - Compliance reporting

## Disclosure Policy

When we receive a security report, we will:

1. Confirm the receipt of your vulnerability report
2. Assess the issue and determine its severity
3. Work on a fix and release plan
4. Notify you when the issue is fixed
5. Credit you for the discovery (unless you prefer to remain anonymous)

## Security Advisories

Security advisories will be published through:
- GitHub Security Advisories
- Release notes
- Project documentation

## Contact

Security Team: 713559+Emasoft@users.noreply.github.com

For general questions, please use [GitHub Discussions](https://github.com/Emasoft/atlasvibe/discussions).
