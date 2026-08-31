# Contributor guide

Start with [CONTRIBUTING.md](../CONTRIBUTING.md). This page covers extension-specific expectations.

Analyzer changes should be deterministic, use machine-readable output where available, preserve category and native rule IDs, restrict work to relevant changed files when correct, and return explicit unavailable/error results. Every subprocess needs a timeout and argument-list invocation. Add fixtures rather than requiring optional tools in the default test suite.

Model/schema changes require JSON serialization tests and a changelog note. Policy changes require boundary tests and must remain independent from score computation. Reporter changes must cap noisy output while preserving all findings in JSON.

Documentation examples must execute against the current CLI, or be clearly labeled as intended/unpublished behavior. Benchmark examples must say when data is synthetic. Use relative links so docs render in forks.
