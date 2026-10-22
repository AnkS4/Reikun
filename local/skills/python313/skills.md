---
name: python-313-modern
description: Write modern, robust, fast, PEP 8-compliant Python 3.13 code. Use this skill whenever writing, reviewing, refactoring, or optimizing Python code, scripts, services, CLIs, libraries, or tests, even when the user does not mention style, typing, or performance. Covers formatting, naming, type hints, error handling, resource management, async, concurrency, profiling-driven optimization, security, testing, and project tooling (uv, ruff, mypy/pyright, pytest).
---

# Python 3.13: Modern, Robust, Optimized Code

Target runtime: **CPython 3.13**. Prefer the standard library, then well-maintained
third-party packages. Correctness first, readability second, speed third (and only
after measuring).

---

## 1. Style (PEP 8, PEP 257)

### Formatting
- 4 spaces per indent, never tabs.
- Line length: PEP 8 says 79 (99 acceptable for teams). Use **88** (ruff/black default) and let the formatter decide. Do not hand-wrap against it.
- Two blank lines around top-level definitions, one between methods.
- Imports at top, one per line, grouped: standard library, third-party, local. Absolute imports preferred. No `from x import *`.
- Trailing commas in multi-line collections and calls (cleaner diffs).
- Use implicit line continuation inside brackets, not backslashes.
- Compare to singletons with `is` / `is not`; use `if items:` not `if len(items) > 0:`.
- Never use bare `except:`; never use `==` with `None`, `True`, `False`.

### Naming
| Kind | Convention | Example |
|---|---|---|
| Module, package | `lower_snake` | `query_rewrite.py` |
| Function, variable, method | `lower_snake` | `build_index()` |
| Class, exception, type alias | `PascalCase` | `SearchResult`, `ParseError` |
| Constant | `UPPER_SNAKE` | `MAX_RETRIES` |
| Internal | leading `_` | `_cache` |
| Type variable (old style) | short `PascalCase` | `T`, `KeyT` |

- Names say what, not how: `retry_count`, not `n`. Avoid single letters except trivial loop indices and comprehensions.
- Booleans read as questions: `is_ready`, `has_items`.
- Exceptions end in `Error`.

### Docstrings (PEP 257)
- Every public module, class, function, and method gets a docstring. Triple double quotes.
- First line: imperative summary, one line, ends with a period.
- Document args, returns, and raises only when not obvious from types and names. Pick one style (Google or NumPy) per project.

```python
def segment(text: str, *, max_chars: int = 100) -> list[Segment]:
    """Split Japanese text into dictionary segments.

    Args:
        text: Raw user input.
        max_chars: Reject inputs longer than this.

    Raises:
        InputTooLongError: If ``text`` exceeds ``max_chars``.
    """
```

- Comments explain **why**, not what. Keep them current or delete them.

---

## 2. Modern language features (use them)

### Typing: always annotate public APIs
Use built-in generics and union syntax. **Do not** import `List`, `Dict`, `Optional`, `Union`.

```python
def lookup(keys: list[str], default: int | None = None) -> dict[str, int]: ...
```

Python 3.12+ syntax for generics and aliases (PEP 695), plus 3.13 TypeVar defaults (PEP 696):

```python
type Pair[T] = tuple[T, T]                 # type alias statement

def first[T](items: Sequence[T]) -> T:     # inline type parameters
    return items[0]

class Box[T = int]:                        # default type parameter (3.13)
    def __init__(self, value: T) -> None:
        self.value = value
```

Other typing tools worth knowing:
- `typing.Self` for fluent/builder returns.
- `@typing.override` to catch signature drift in subclasses.
- `typing.TypeIs` (PEP 742, 3.13) for precise narrowing functions; prefer over `TypeGuard`.
- `typing.ReadOnly` (PEP 705, 3.13) for `TypedDict` fields.
- `typing.Protocol` for structural interfaces; `Literal`, `Final`, `NamedTuple`, `TypedDict`, `Required`/`NotRequired`.
- Avoid `Any`. If unavoidable, confine it to a narrow boundary and comment why.
- Use `collections.abc` types (`Sequence`, `Mapping`, `Iterable`) for parameters; concrete types for returns.

### Data containers
Choose deliberately:
- `@dataclass(slots=True, frozen=True, kw_only=True)` for internal records (immutable by default, lower memory, faster attribute access).
- `NamedTuple` for small immutable tuples that must unpack.
- `TypedDict` for JSON-shaped dicts crossing boundaries.
- Pydantic (v2) or `msgspec` for validating **untrusted external input**.
- Plain `dict` only when keys are truly dynamic.

```python
from dataclasses import dataclass, field, replace

@dataclass(slots=True, frozen=True, kw_only=True)
class Entry:
    id: int
    forms: tuple[str, ...] = ()
    score: float = 0.0
    tags: frozenset[str] = field(default_factory=frozenset)

updated = replace(entry, score=1.0)      # or copy.replace(entry, score=1.0) in 3.13
```

### Other modern idioms
- **f-strings** everywhere (PEP 701 lifts nesting and quoting limits in 3.12+). For logging, use lazy `%s` args instead (see section 4).
- **Structural pattern matching** (`match`) for dispatch on shape or type; not as a glorified `if/elif` on one value.
- **Walrus** `:=` only when it removes a duplicate call and stays readable.
- **`enum.StrEnum` / `IntEnum`** over string constants.
- **`pathlib.Path`** over `os.path`. Always pass `encoding="utf-8"` to `open()` / `read_text()`.
- **`itertools.batched`** (3.12) for chunking; `itertools.pairwise`; `zip(..., strict=True)` when lengths must match.
- **`tomllib`** for reading TOML (stdlib).
- **`datetime.now(UTC)`** (`from datetime import UTC`); never `datetime.utcnow()` (deprecated) and avoid naive datetimes. Use `zoneinfo` for time zones.
- **`warnings.deprecated`** (PEP 702, 3.13) to mark deprecated functions and classes.
- **`ExceptionGroup` / `except*`** with `asyncio.TaskGroup` for concurrent failures.
- Positional-only `/` and keyword-only `*` in signatures to lock down APIs.

### Removed or discouraged in 3.13
- PEP 594 "dead batteries" removed: `cgi`, `cgitb`, `crypt`, `imghdr`, `telnetlib`, `pipes`, `nntplib`, `audioop`, `aifc`, `sunau`, `uu`, `xdrlib`, `chunk`, `mailcap`, `msilib`, `nis`, `ossaudiodev`, `spwd`, `sndhdr`. Use maintained alternatives.
- `locals()` in functions now has defined snapshot semantics (PEP 667); do not rely on mutating it.
- Docstring leading indentation is stripped at compile time; no behavior change, slightly smaller `.pyc`.

---

## 3. Design principles

- **Small, single-purpose functions**; pure where possible. Push I/O to the edges.
- **Composition over inheritance.** Use `Protocol` for seams instead of deep class trees.
- **Explicit over implicit**; no hidden global state. Pass dependencies in.
- **Make illegal states unrepresentable**: enums, frozen dataclasses, `Literal`, validated constructors.
- **Never use mutable default arguments.** Use `None` or `field(default_factory=...)`.
- **Return early** to flatten nesting; avoid flag variables.
- **Validate at boundaries** (HTTP, CLI, files, env), trust internally. Parse, don't validate: convert raw input into typed objects once.
- Configuration from environment via one typed settings object (e.g. `pydantic-settings`), validated at import or startup, fail fast with a clear message.
- `if __name__ == "__main__":` guard for runnable modules; keep `main()` thin.

---

## 4. Robustness

### Exceptions
- Catch the **narrowest** exception that you can actually handle. Never swallow silently.
- Chain causes: `raise DomainError("...") from exc`.
- Define a small project exception hierarchy rooted in one base class.
- Keep `try` bodies minimal. Use `else` for the success path and `finally` (or context managers) for cleanup.
- Use `contextlib.suppress(SpecificError)` only for genuinely ignorable errors.
- Use `exc.add_note("context")` (3.11+) to attach debugging context.

```python
try:
    raw = path.read_text(encoding="utf-8")
except FileNotFoundError as exc:
    raise ConfigError(f"Missing config file: {path}") from exc
else:
    return parse(raw)
```

### Resources
- Always use `with` for files, locks, sockets, DB connections, temp files, subprocesses.
- Write your own with `contextlib.contextmanager` / `asynccontextmanager`.
- Use `tempfile` and atomic writes (write to temp, then `os.replace`) for files others may read.

### Logging, not print
```python
import logging

logger = logging.getLogger(__name__)      # one per module
logger.info("Indexed %d entries in %.1f s", count, elapsed)   # lazy formatting
logger.exception("Embedding failed for id=%s", entry_id)      # inside except
```
- Configure handlers once, at the application entry point. Libraries never configure logging.
- Never log secrets or raw personal data.

### Network, subprocess, and time
- **Every** network call has a timeout (`httpx.Client(timeout=10.0)`). Retry only idempotent operations, with exponential backoff and jitter, bounded attempts.
- `subprocess.run([...], check=True, capture_output=True, text=True, timeout=...)` with a **list** of args, never `shell=True` with interpolated input.
- Use `time.perf_counter()` for durations, `time.monotonic()` for deadlines; never `time.time()` for either.

### Security
- Never `eval`/`exec` untrusted input; never `pickle.loads` untrusted data; use `yaml.safe_load`.
- Parameterized SQL only (`cursor.execute("... WHERE id = ?", (id_,))`).
- `secrets` module for tokens, `hmac.compare_digest` for comparing secrets.
- Secrets from environment or a secret manager, never in source control.
- Resolve and check user-supplied paths (`Path.resolve()`, confirm inside an allowed root).
- Pin and audit dependencies (`uv.lock`, `pip-audit`).

---

## 5. Performance (measure first)

**Process:** correctness, then profile, then optimize the hot spot, then re-measure. Never optimize on intuition.

### Measure
- `python -m timeit` / `timeit.repeat` for micro-benchmarks.
- `cProfile` + `snakeviz`, or `py-spy` (sampling, attachable to a running process) for real workloads.
- `tracemalloc` for memory; `pytest-benchmark` for regression tracking.

### Algorithmic wins (usually 10-1000x)
- Membership tests on `set` / `dict`, not `list`.
- Sort once; use `bisect` for sorted lookups, `heapq` for top-k (`heapq.nsmallest/nlargest`).
- `collections.deque` for queues, `Counter` / `defaultdict` for tallies.
- Build strings with `"".join(parts)`, not `+=` in loops.
- Avoid repeated work: hoist invariants, precompute, cache.

### Idiomatic speedups
- Comprehensions and generator expressions over manual append loops; generators when the consumer streams.
- Built-ins (`sum`, `min`, `max`, `any`, `all`, `sorted`, `map` with C functions) run in C.
- `@dataclass(slots=True)` / `__slots__` for many small objects.
- Local variable binding in tight loops (`append = out.append`) only after profiling proves it matters.
- `functools.cache` for pure functions with a small/fixed input domain; `lru_cache(maxsize=N)` when inputs are open-ended or user-controlled (unbounded caches are memory leaks). Cached return values are shared: return immutable objects.
- Stream large files line by line or in chunks; use `mmap` for huge binary files.
- Use `re.compile` for patterns reused across calls at module level.

### Choose the concurrency model by workload
| Workload | Tool |
|---|---|
| Many concurrent I/O waits (HTTP, DB) | `asyncio` (`TaskGroup`, `asyncio.timeout`) |
| Blocking I/O inside async code | `asyncio.to_thread(...)` |
| Blocking I/O in sync code | `ThreadPoolExecutor` |
| CPU-bound pure Python | `ProcessPoolExecutor` / `multiprocessing` |
| Numeric arrays | NumPy / Polars (vectorize, no Python loops) |
| Hot loop that cannot be vectorized | Cython, Numba, Rust (PyO3) |

```python
async def fetch_all(urls: Sequence[str]) -> list[bytes]:
    async with httpx.AsyncClient(timeout=10.0) as client, asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(client.get(u)) for u in urls]
    return [t.result().content for t in tasks]
```

Async rules: never call blocking code in a coroutine; always `await` or hold task references; bound concurrency with `asyncio.Semaphore`; use `asyncio.timeout()` around external calls.

### 3.13 runtime notes (experimental; do not enable blindly in production)
- **Free-threaded build** (`python3.13t`, PEP 703): GIL can be disabled (`PYTHON_GIL=0`). Single-thread speed is lower and many C extensions are not yet compatible. Benchmark and test thoroughly before adopting; thread-safe code is still your responsibility (locks, `queue.Queue`).
- **Experimental JIT** (PEP 744): opt-in build flag, modest gains today. Not a substitute for profiling.
- Default interpreter gets general speedups each release; staying current is itself an optimization.

---

## 6. Testing and quality gates

- **pytest** with plain `assert`, fixtures, `@pytest.mark.parametrize`. One behavior per test, arrange-act-assert.
- Test public behavior, edge cases (empty, huge, unicode, boundary), and failure paths (`pytest.raises(..., match=...)`).
- Property-based tests with **Hypothesis** for parsers, normalizers, round-trips.
- Isolate I/O with fakes or `monkeypatch`; mock at boundaries, not internals. Use `tmp_path` for files.
- Coverage as a signal (`pytest-cov`, branch coverage), not a goal. Gate on regressions.
- Deterministic tests: seed randomness, inject clocks, no network.

---

## 7. Tooling and project layout

Use **uv** for environments, locking, and running; **ruff** for lint and format; **mypy** (strict) or **pyright** for types.

```
project/
├── pyproject.toml
├── uv.lock
├── src/
│   └── package_name/
│       ├── __init__.py
│       └── core.py
└── tests/
```

Starter `pyproject.toml` fragment:

```toml
[project]
name = "package-name"
requires-python = ">=3.13"

[tool.ruff]
line-length = 88
target-version = "py313"

[tool.ruff.lint]
select = [
  "E", "W",   # pycodestyle (PEP 8)
  "F",        # pyflakes
  "I",        # isort
  "N",        # pep8-naming
  "D",        # pydocstyle (set a convention below)
  "UP",       # pyupgrade (modernize syntax)
  "B",        # bugbear
  "C4",       # comprehensions
  "SIM",      # simplify
  "PTH",      # use pathlib
  "RUF",      # ruff-specific
  "S",        # bandit (security)
  "PERF",     # perflint
  "ANN",      # annotations
  "ASYNC",    # async pitfalls
  "T20",      # no stray print()
]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.mypy]
python_version = "3.13"
strict = true
```

Commands:
```bash
uv sync                      # install from lockfile
uv run ruff format .         # format
uv run ruff check --fix .    # lint
uv run mypy src              # type-check
uv run pytest -q             # test
```

Run these in pre-commit and CI; fail the build on any of them.

---

## 8. Quick review checklist

Before finishing any Python change, confirm:

- [ ] Formatted and lint-clean (ruff); no unused imports or variables.
- [ ] Public functions fully type-annotated using `list[str]`, `X | None`, and PEP 695 syntax where it fits.
- [ ] Docstrings on public API; comments explain why.
- [ ] No mutable default args, bare `except`, `print` debugging, `shell=True`, or `eval`.
- [ ] Specific exceptions, chained with `from`; resources in `with`.
- [ ] Every external call has a timeout; retries are bounded.
- [ ] `encoding="utf-8"` on text I/O; `pathlib` for paths; timezone-aware datetimes.
- [ ] Caches have an explicit bound unless the input domain is fixed.
- [ ] Any optimization is backed by a measurement.
- [ ] Tests cover happy path, edge cases, and failures.

---

## 9. When in doubt

1. Follow PEP 8 and let `ruff format` settle style arguments.
2. Prefer the simplest code that is correct, typed, and tested.
3. Prefer the standard library until a dependency clearly earns its place.
4. Be explicit about trade-offs when deviating from these defaults, and leave a short comment explaining why.
