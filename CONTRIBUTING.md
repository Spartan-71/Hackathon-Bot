# Contributing to HackRadar

Thank you for showing interest in contributing to **HackRadar**! We welcome all kinds of contributions — bug fixes, new scrapers, feature requests, or improvements to the documentation.


## 🛠️ How to Contribute

1. **Fork the repo** and clone your fork locally:
   ```bash
   git clone https://github.com/username/Discord-Hackathon-Bot.git
   cd Discord-Hackathon-Bot
   ```

2. **Set up your development environment**:
   ```bash
   # (Recommended) Create and activate a virtual environment with uv
   uv venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate

   # Install dependencies including dev dependencies
   uv sync

   # Set up pre-commit hooks
   uv run pre-commit install
   ```

3. **Create a new branch**:
   ```bash
   git checkout -b your-feature-name
   ```

4. **Make your changes** following the guidelines below.

5. **Run tests and pre-commit hooks** (see sections below).

6. **Commit and push your changes**:
   ```bash
   git commit -m "Add your message here"
   git push origin your-feature-name
   ```

7. **Open a Pull Request** on GitHub.


## 🧪 Running Tests

Before submitting your PR, ensure all tests pass:

```bash
uv run pytest --all-files
```

**Important**: All tests must pass before your PR can be merged. If you're adding new features, please add corresponding tests.

## 🔧 Pre-commit Hooks

This project uses pre-commit hooks to ensure code quality. The hooks will automatically:
- Remove trailing whitespace
- Fix end-of-file issues
- Check YAML syntax
- Detect merge conflicts
- Run Ruff linter and formatter

### Setting up pre-commit hooks

```bash
# Install pre-commit hooks (run once after cloning)
uv run pre-commit install
```

### Running pre-commit hooks manually

```bash
# Run hooks on all files
uv run pre-commit run --all-files

# Run hooks on staged files only (automatic before commit)
uv run pre-commit run
```

**Note**: Pre-commit hooks run automatically before each commit. If a hook fails, fix the issues and try committing again.

## ✅ Guidelines

* Follow existing code structure and naming conventions.
* Keep your changes focused and minimal.
* Write clear and concise commit messages.
* If adding a new scraper, place it in the `adapters/` folder.
* Ensure all tests pass before submitting a PR.
* Run pre-commit hooks (or let them run automatically) before committing.


## 📞 Need Help?

Feel free to open an issue or discussion if you have any questions.

We’re glad to have you here 💙
