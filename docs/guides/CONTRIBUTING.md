# 🤝 Contributing Guide

Thank you for your interest in contributing to ParagonOCR Web Edition!

## Getting Started

1. **Fork the repository**
2. **Clone your fork:**
   ```bash
   git clone https://github.com/your-username/ParagonOCR.git
   cd ParagonOCR
   ```
3. **Create a branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **Follow the development setup:** See [SETUP_DEV.md](SETUP_DEV.md)

## Development Guidelines

### Code Style

#### Python (Backend)
- Follow **PEP 8** style guide
- Use **Black** for formatting (line length: 100)
- Use **isort** for import sorting
- Type hints are encouraged

**Format code:**
```bash
black app/
isort app/
```

#### TypeScript/React (Frontend)
- Follow **ESLint** rules
- Use **Prettier** for formatting
- Use **TypeScript** strict mode
- Prefer functional components with hooks

**Format code:**
```bash
npm run format
npm run lint
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(receipts): add receipt export functionality
fix(ocr): handle PDF conversion errors gracefully
docs(api): update API reference with new endpoints
```

### Pull Request Process

1. **Update documentation** if needed
2. **Add tests** for new features
3. **Ensure all tests pass:**
   ```bash
   # Backend
   pytest tests/ -v
   
   # Frontend
   npm run test
   ```
4. **Update CHANGELOG.md** (if applicable)
5. **Create pull request** with clear description

### Testing Requirements

- **New features** must include tests
- **Bug fixes** must include regression tests
- **Target coverage:** 80%+ for new code
- **All tests** must pass before PR submission

### Documentation

- **Code comments** for complex logic
- **Docstrings** for all public functions/classes
- **API documentation** updated for endpoint changes
- **README updates** for new features

## Project Structure

### Backend
```
backend/app/
├── main.py           # FastAPI app
├── config.py         # Configuration
├── database.py       # Database setup
├── models/           # SQLAlchemy models
├── routers/          # API endpoints
├── services/         # Business logic
└── schemas.py        # Pydantic schemas
```

### Frontend
```
frontend/src/
├── pages/            # Page components
├── components/       # Reusable components
├── store/            # Zustand stores
├── lib/              # Utilities
└── main.tsx          # Entry point
```

## Feature Development

### Adding a New Feature

1. **Create feature branch:**
   ```bash
   git checkout -b feature/new-feature
   ```

2. **Implement feature:**
   - Backend: Add router/service/model
   - Frontend: Add component/page/store
   - Database: Create migration if needed

3. **Add tests:**
   - Unit tests for business logic
   - Integration tests for API endpoints
   - Component tests for UI

4. **Update documentation:**
   - API reference (if new endpoints)
   - Architecture docs (if significant changes)
   - User guide (if user-facing)

5. **Submit PR:**
   - Clear description
   - Link to related issues
   - Screenshots (if UI changes)

### Adding a New API Endpoint

1. **Create router function:**
   ```python
   @router.post("/new-endpoint")
   async def new_endpoint(
       request: NewRequest,
       db: Session = Depends(get_db),
       current_user=Depends(get_current_user),
   ):
       """Endpoint description."""
       # Implementation
   ```

2. **Add Pydantic schemas:**
   ```python
   class NewRequest(BaseModel):
       field: str
   ```

3. **Add service logic:**
   ```python
   # In services/new_service.py
   class NewService:
       def process(self, data: NewRequest) -> Result:
           # Business logic
   ```

4. **Add tests:**
   ```python
   def test_new_endpoint(client, auth_token):
       response = client.post(
           "/api/new-endpoint",
           json={"field": "value"},
           headers={"Authorization": f"Bearer {auth_token}"}
       )
       assert response.status_code == 200
   ```

## Bug Reports

### Before Submitting

1. **Check existing issues** - may already be reported
2. **Reproduce the bug** - ensure it's reproducible
3. **Gather information:**
   - Error messages
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details

### Bug Report Template

```markdown
**Description:**
Clear description of the bug

**Steps to Reproduce:**
1. Step one
2. Step two
3. See error

**Expected Behavior:**
What should happen

**Actual Behavior:**
What actually happens

**Environment:**
- OS: [e.g., Ubuntu 22.04]
- Python: [e.g., 3.11]
- Node: [e.g., 20.x]
- Version: [e.g., 1.0.0-beta]

**Error Logs:**
```
Paste error logs here
```

**Screenshots:**
If applicable
```

## Feature Requests

### Before Submitting

1. **Check existing issues** - may already be requested
2. **Consider scope** - is it within project goals?
3. **Think about implementation** - rough approach

### Feature Request Template

```markdown
**Feature Description:**
Clear description of the feature

**Use Case:**
Why is this feature needed?

**Proposed Solution:**
How should it work?

**Alternatives Considered:**
Other approaches considered

**Additional Context:**
Any other relevant information
```

## Code Review

### For Contributors

- **Be responsive** to review feedback
- **Address comments** promptly
- **Ask questions** if unclear
- **Be open to suggestions**

### For Reviewers

- **Be constructive** in feedback
- **Explain reasoning** for suggestions
- **Approve promptly** if changes look good
- **Request changes** with clear guidance

## Questions?

- **Open an issue** for bug reports or feature requests
- **Check documentation** in `docs/` directory
- **Review existing issues** for similar questions

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

**Thank you for contributing!** 🎉

**Last Updated:** 2025-12-07  
**Version:** 1.0.0-beta

