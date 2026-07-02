SOLID REVIEW — issues #14 & #16 (env-file auth verification + Apple Keychain wizard) — 2026-07-02 20:30 UTC

Scope expanded: none
  Step 0a: Callers of auth.py = __main__.py, tests/test_auth.py (both read).
  Step 0b: keychain_service / keychain_account consumed only in auth.py:109 and tests.
  Step 0c: AuthConfig constructed at config.py:52, tests/test_auth.py:21, tests/test_config.py:99.
  No additional files added to scope beyond what was explicitly provided.

Review scope: src/gemini_bridge/auth.py, src/gemini_bridge/config.py,
  src/gemini_bridge/__main__.py, tests/test_auth.py, tests/test_config.py.
Focus: Python correctness for new auth methods. setup.sh and docs excluded per brief.

Scores:
  S — Single Responsibility: 9/10
  O — Open/Closed:           7/10
  L — Liskov Substitution:  10/10
  I — Interface Segregation:  8/10
  D — Dependency Inversion:   9/10
  OVERALL:                    7.4/10

  Formula: round((9*1.5 + 9*1.5 + 7 + 10 + 8) / 7.0, 1) = round(52.0 / 7.0, 1) = 7.4

Summary:

The Python implementation supporting issues #14 and #16 is solid overall. auth.py,
config.py, and __main__.py each have a clear, single job and the module boundaries are
respected: credentials flow outward from auth.py as an abstraction, client.py never
constructs its own credentials, and __main__.py orchestrates without containing logic.

The primary gap is an OCP inconsistency in build_credentials (auth.py:105-113): adc and
env are dispatched through the extensible _LOADERS dict, but keychain is handled by a
hardcoded if branch because it requires extra arguments (service, account) that the
_CredLoader Callable type does not accommodate. The _LOADERS pattern signals
"add a method here, no modification needed," but that promise only holds for zero-argument
methods. Any future parameterized method (e.g., workload identity with an audience string)
forces another if branch. The dict creates a false extensibility signal.

A secondary ISP observation: AuthConfig always carries keychain_service and
keychain_account even when method is "adc" or "env". There is no model_validator that
makes these fields absent or inert for non-keychain configs. In practice the defaults
hide this, but a discriminated union or a conditional validator would make the contract
precise. This is minor at current scale.

Both issues are documented and manageable without a code rewrite now.

Gaps:

  [O] build_credentials uses split dispatch: _LOADERS dict for zero-arg methods (adc,
  env) and a hardcoded if method == "keychain" branch for parameterized methods.
  The _LOADERS dict signals extensibility it cannot deliver for any method that needs
  fields beyond method name. — auth.py:105-113
    Realistic to fix now: YES
    Why: Changing _CredLoader to Callable[[AuthConfig], Credentials] and moving all
    loaders (including _load_keychain) into the dict unifies dispatch and closes
    build_credentials against modification for future methods.

  [I] AuthConfig always includes keychain_service: str = "gemini-bridge" and
  keychain_account: str = "vertex-sa" regardless of method. These fields are dead for
  adc and env configs — constructed and passed through but never read downstream.
  No model_validator enforces their irrelevance for non-keychain methods. — config.py:40-43
    Realistic to fix now: YES (low priority)
    Why: A @model_validator(mode="after") that checks keychain fields are only meaningful
    when method == "keychain", or a discriminated union, eliminates the dead interface.
    Current defaults make this invisible in practice but the schema is imprecise.

  [S] _load_adc and _load_env are functionally identical: both call
  google.auth.default(scopes=_VERTEX_SCOPES) with identical success/failure paths.
  The only difference is the error message text. The "adc" vs "env" distinction is
  a config-label distinction that does not map to any implementation distinction —
  google.auth.default() internally handles both GOOGLE_APPLICATION_CREDENTIALS and
  gcloud ADC in one call. This is not a SRP violation but the parallel functions
  suggest the abstraction boundary is fuzzy. — auth.py:43-63
    Realistic to fix now: NO
    Why: Collapsing them would break the intentional user-facing error message
    distinction, which has documentation value. Acceptable as-is; worth a comment
    in the code noting why two functions call the same underlying API.

RECOMMENDATION: CONDITIONAL PASS

Reason: Overall 7.4, no principle below 7. The OCP gap in build_credentials (split
dispatch between _LOADERS dict and hardcoded if-branch for keychain) is the most
concrete deficiency — it will require modification of build_credentials for every
future parameterized auth method. The ISP gap in AuthConfig (dead keychain fields for
adc/env methods) is secondary. Both are well-contained and appropriate to file as
issues and address in a follow-up; neither blocks the current feature ship.

Proceed: file a GitHub issue against auth.py:105-113 (OCP) and config.py:40-43 (ISP)
before closing these issues.
