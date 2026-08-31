# Releasing AgentGuard

Releases are built only from an exact `vMAJOR.MINOR.PATCH` tag matching the version in
`pyproject.toml`. The release workflow builds the wheel and source archive once, runs strict Twine
metadata checks, verifies archive contents, installs the wheel in a clean virtual environment, and
runs `agentguard version` and `agentguard doctor` before publication.

PyPI publication uses GitHub Actions trusted publishing; no long-lived PyPI token belongs in the
repository. Before the first release, configure a protected GitHub environment named `pypi` with
required reviewer approval and register this repository/release workflow as a trusted publisher on
PyPI. The publish job receives only `contents: read`, `id-token: write`, and `attestations: write`.
Build provenance is generated for both distribution artifacts. Test the identical package name and
workflow through the manual `Publish candidate to TestPyPI` workflow before creating the production
tag. Configure its protected `testpypi` environment as a TestPyPI trusted publisher as well.
Production publication remains blocked until the protected `pypi` environment is approved.

After PyPI succeeds, the workflow creates GitHub release notes and attaches the verified artifacts.
Immutable patch tags such as `v1.2.3` are never moved. For GitHub Action consumers, maintainers may
move the convenience `v1` tag only to a fully validated backward-compatible `v1.x.y` release. Moving
`v1` is a separate reviewed operation and is intentionally not automated by the release workflow.

Release checklist:

1. Update `CHANGELOG.md` and the project version.
2. Run tests, Ruff, mypy, distribution build/check, clean-wheel smoke tests, and the consumer Action
   smoke workflow.
3. Publish and install the candidate on TestPyPI without changing the production workflow.
4. Create and push the exact immutable version tag only after explicit release approval.
5. Approve the protected `pypi` environment, observe publication and provenance, then verify the
   generated GitHub release.
