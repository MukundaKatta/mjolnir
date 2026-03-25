# Contributing to Mjolnir

Contributions are welcome! Follow these guidelines to keep the project consistent.

## Getting started

```bash
git clone https://github.com/MukundaKatta/mjolnir.git
cd mjolnir
PYTHONPATH=src python3 -m pytest tests/ -v --tb=short
```

## Development workflow

1. Create a feature branch from `main`.
2. Write code in `src/mjolnir/`.
3. Add tests in `tests/`.
4. Ensure all tests pass: `make test`.
5. Open a pull request.

## Code style

- Python 3.9 compatible (use `from __future__ import annotations`).
- No external dependencies in core modules.
- Use type hints throughout.
- Docstrings follow Google/NumPy conventions.

## Testing

- Every public class and function should have at least one test.
- Run with: `PYTHONPATH=src python3 -m pytest tests/ -v --tb=short`

## Commit messages

Use concise, imperative-mood subjects:

```
feat: add histogram metric type
fix: handle zero context limit in snapshot
test: cover alert callback ordering
```
