Build the library "$ARGUMENTS" for macOS, for each deployment target still published (12.0 and 13.0, see `.claude/rules/working-here.md`):
- ARM64 Release: python3 build.py --macos-sdk <12.0|13.0> --arch arm64 --build-type Release --library $ARGUMENTS --no-deps
- x86_64 Release: python3 build.py --macos-sdk <12.0|13.0> --arch x86_64 --build-type Release --library $ARGUMENTS --no-deps
A `--no-deps` run skips DependenciesTest: run it by hand before any publish.
Report success/failure for each target and architecture.
