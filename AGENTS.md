# Junior Counsel Development Agents

This document describes the specialized AI agents available for development assistance in the Junior Counsel project.

## Available Agents

### Core Development Agents

#### 1. `/qa-test` - QA & Testing Agent
**Purpose**: Comprehensive quality assurance and testing for backend APIs and frontend components.

**Capabilities**:
- Analyze test coverage and identify gaps
- Generate unit tests for repositories, services, and utilities
- Create integration tests for API endpoints
- Write frontend component tests (React Testing Library)
- Generate test fixtures and mock data
- Run tests with coverage reporting
- Performance and security testing
- E2E test scenarios

**When to Use**: Before deploying new features, when test coverage drops, for performance benchmarking

---

#### 2. `/ba-review` - Business Analyst Agent
**Purpose**: Ensure development aligns with customer requirements and original documentation.

**Capabilities**:
- Requirements traceability (BR-*, FR-*, NFR-*)
- Gap analysis between spec and implementation
- Scope change detection and logging
- Business value validation
- Documentation consistency checks
- Stakeholder communication summaries

**When to Use**: At feature start, during sprint planning, before major releases, when scope creep is suspected

**Key Focus**: Ensures court-ready drafting remains #1 priority and serves target users (advocates, attorneys)

---

#### 3. `/arch-review` - Software Architecture Agent
**Purpose**: Maintain architecture quality, scalability, and compliance with design patterns.

**Capabilities**:
- Architecture compliance review
- **Database design validation** (indexes, schemas, pgvector)
- **API pagination enforcement** (all list endpoints must paginate)
- Worker-based pattern validation (no heavy work in API handlers)
- Scalability assessment
- Technical debt identification
- Security architecture review
- Performance optimization

**When to Use**: Before merging structural changes, when adding API endpoints, database schema changes, scaling

**Critical Checks**:
- ✅ All heavy operations in workers (NOT API handlers)
- ✅ Database indexes on frequently queried fields
- ✅ Pagination on all list endpoints
- ✅ Organisation scoping on multi-tenant entities

---

#### 4. `/frontend-dev` - Frontend Development Agent
**Purpose**: Ensure frontend code follows React/Next.js best practices and delivers excellent UX.

**Capabilities**:
- React/Next.js code review
- TypeScript type safety validation
- Accessibility (a11y) compliance
- Performance optimization
- API integration patterns (React Query)
- Form handling best practices
- Component testing
- Legal domain UX validation

**When to Use**: Before implementing UI features, during code reviews, accessibility issues, performance optimization

**Best Practices Enforced**:
- TypeScript strict mode (no `any`)
- Semantic HTML and ARIA labels
- React Query for API state
- Legal terminology (not generic tech terms)

---

### Specialized Agents

#### 5. `/security-audit` - Security & Compliance Agent
**Purpose**: Ensure security standards and South African data protection (POPIA) compliance.

**Capabilities**:
- Authentication and authorization review
- SQL injection prevention
- XSS/CSRF protection
- File upload security validation
- POPIA compliance checks (data export, deletion, retention)
- Audit logging verification
- Dependency vulnerability scanning
- Multi-tenant data isolation verification

**When to Use**: Before production deployment, security incidents, compliance audits, penetration testing

**Critical Focus**:
- Password hashing (no plain text)
- Organisation data isolation
- Legal document confidentiality
- South African data residency

---

#### 6. `/worker-review` - Worker & Queue Agent
**Purpose**: Validate queue-based architecture and worker implementation.

**Capabilities**:
- Verify no heavy work in API handlers
- Check job handler idempotency
- Validate event emission
- Monitor queue health
- Retry logic validation
- Worker scaling recommendations

**When to Use**: When adding new background jobs, queue performance issues, scaling workers

**Critical Pattern**:
```
API: Validate → Create Record → Enqueue Job → Return 202
Worker: Poll Queue → Process → Update Status → Emit Event
```

---

#### 7. `/api-doc` - API Documentation Agent
**Purpose**: Generate and maintain comprehensive API documentation.

**Capabilities**:
- OpenAPI/Swagger spec generation
- Validate endpoint documentation
- Create integration examples
- TypeScript types generation
- Maintain API changelog
- Version migration guides

**When to Use**: After adding new endpoints, before frontend integration, for external API consumers

**Standards Enforced**:
- All endpoints documented
- Pagination on list endpoints
- Consistent response/error formats
- Code samples provided

---

#### 8. `/perf-test` - Performance Testing Agent
**Purpose**: Ensure system meets performance targets and scalability goals.

**Capabilities**:
- Load testing (Locust, k6)
- Database query optimization
- pgvector search benchmarking
- Worker throughput analysis
- API profiling
- Frontend performance testing (Core Web Vitals)
- Bottleneck identification

**When to Use**: Before production, performance issues, capacity planning, scalability testing

**Performance Targets**:
- Upload/enqueue: < 3s
- Search queries: 1-2s
- Q&A/drafting: < 5-8s
- 10,000+ concurrent users

---

#### 9. `/ui-design` - UI/UX Design Agent
**Purpose**: Ensure design consistency with original system and legal domain best practices.

**Capabilities**:
- Extract design patterns from old system
- Create design specifications (colors, typography, spacing)
- Review UI components for consistency
- Validate legal terminology usage
- Accessibility compliance (WCAG 2.1 AA)
- Responsive design validation

**When to Use**: Before implementing new UI, design reviews, when diverging from old system

**Reference Systems**:
- QA Website: https://qa.juniorcounsel.co.za (friedman@law.co.za / Anshal789$)
- Gitea: https://gitea.cyber-mint.com/ (adrian.friedman / Anshal789$)
- Old codebase: `old code/jc/`

**Critical**: Use legal terminology (Affidavit, Pleading, Heads of Argument), NOT generic tech terms

---

## Agent Quick Reference

| Agent | Command | Primary Focus | Output |
|-------|---------|---------------|--------|
| QA & Testing | `/qa-test` | Test coverage, quality | Test suite, coverage report |
| Business Analyst | `/ba-review` | Requirements alignment | Traceability matrix, gaps |
| Software Architect | `/arch-review` | Architecture, DB, pagination | Compliance report, tech debt |
| Frontend Dev | `/frontend-dev` | React/Next.js, UX | Code review, UX validation |
| Security Audit | `/security-audit` | Security, POPIA compliance | Vulnerability list, fixes |
| Worker Review | `/worker-review` | Queue architecture | Worker compliance report |
| API Documentation | `/api-doc` | OpenAPI specs | API spec, TypeScript types |
| Performance Test | `/perf-test` | Load testing, optimization | Performance report, bottlenecks |
| UI Design | `/ui-design` | Design consistency, a11y | Design spec, mockups |

---

## Agent Workflows

### New Feature Development

1. **Business Analyst** → Verify feature is in requirements
   ```bash
   /ba-review
   ```

2. **Software Architect** → Validate architecture approach, database design, pagination
   ```bash
   /arch-review
   ```

3. **QA Testing** → Write tests first (TDD)
   ```bash
   /qa-test
   ```

4. **Frontend Dev** → Implement UI with best practices
   ```bash
   /frontend-dev
   ```

5. **UI Design** → Ensure consistency with old system
   ```bash
   /ui-design
   ```

### Pre-Production Checklist

Run all agents in sequence:

```bash
/qa-test         # All tests pass, coverage >80%
/ba-review       # All MVP requirements met
/arch-review     # Architecture compliant, DB optimized
/security-audit  # No critical vulnerabilities
/worker-review   # Queue architecture correct
/perf-test       # Performance targets met
/api-doc         # API fully documented
/ui-design       # Design consistent, accessible
```

### Weekly Maintenance

```bash
/security-audit  # Check for new vulnerabilities
/perf-test       # Monitor performance trends
/arch-review     # Review technical debt
```

---

## Common Scenarios

### Adding a New API Endpoint

1. `/arch-review` - Ensure design follows patterns (pagination, error handling)
2. `/api-doc` - Document endpoint in OpenAPI spec
3. `/qa-test` - Write unit and integration tests
4. `/security-audit` - Check authentication, authorization, input validation

### Implementing Background Job

1. `/arch-review` - Verify API enqueues only (no heavy work)
2. `/worker-review` - Validate idempotency, event emission, status tracking
3. `/qa-test` - Test job handler with mocked dependencies

### Building New UI Feature

1. `/ui-design` - Extract patterns from old system, create mockups
2. `/frontend-dev` - Implement with React/Next.js best practices
3. `/qa-test` - Write component tests, check accessibility
4. `/perf-test` - Validate Core Web Vitals

### Database Schema Change

1. `/arch-review` - Review indexes, constraints, organisation scoping
2. `/ba-review` - Verify aligns with requirements
3. `/perf-test` - Benchmark query performance
4. `/qa-test` - Test migrations, data integrity

---

## Agent Best Practices

### When to Use Multiple Agents

**Parallel**: Run agents that don't depend on each other in parallel
```bash
# In one session
/security-audit
/perf-test
/api-doc
```

**Sequential**: Run agents that build on each other sequentially
```bash
/ba-review        # First: Verify requirement exists
/arch-review      # Then: Design solution
/qa-test          # Then: Test implementation
```

### Agent Output

Each agent provides:
- **Status Report**: What's working vs. what needs attention
- **Action Items**: Specific fixes with priority
- **Code Examples**: How to implement recommendations
- **Documentation**: Updates to specs, guides, READMEs

### Customizing Agents

To modify an agent:
1. Edit `.claude/commands/{agent-name}.md`
2. Update the agent's focus or tasks
3. Changes take effect immediately

To create a new agent:
```bash
touch .claude/commands/my-agent.md
```

Add frontmatter:
```markdown
---
description: Brief description of agent
---

You are a [Role] for the Junior Counsel system...
```

---

## Integration with Development Process

### Git Workflow

```bash
# Feature branch
git checkout -b feature/new-drafting-ui

# Before committing
/arch-review      # Check architecture
/qa-test          # Run tests
/security-audit   # Security check

# Commit
git add .
git commit -m "Add new drafting UI"

# Before PR
/ba-review        # Verify requirements met
/frontend-dev     # Review code quality
/ui-design        # Check design consistency

# Create PR
```

### CI/CD Integration

Agents can be integrated into CI/CD pipelines:
- `/qa-test` → Run in CI (pytest, coverage)
- `/security-audit` → Dependency scanning (pip-audit)
- `/perf-test` → Load tests on staging
- `/api-doc` → Generate OpenAPI spec

---

## Support and Feedback

### Getting Help

- **Agent not working?** Check `.claude/commands/{agent}.md` for syntax errors
- **Need different focus?** Edit the agent's task list
- **Want new agent?** Create one following the pattern above

### Providing Feedback

- **Agent missed something?** Update its task list to include it
- **Agent too verbose?** Adjust the deliverables section
- **Agent conflicts with another?** Coordinate their focus areas

---

## Summary

Junior Counsel has **9 specialized agents** covering:
- ✅ Testing & QA
- ✅ Business Requirements
- ✅ Software Architecture
- ✅ Frontend Development
- ✅ Security & Compliance
- ✅ Worker & Queue Architecture
- ✅ API Documentation
- ✅ Performance Testing
- ✅ UI/UX Design

Use them throughout development to maintain high quality, meet customer requirements, and build a scalable, secure legal document processing system.

---

**Last Updated**: March 11, 2026
