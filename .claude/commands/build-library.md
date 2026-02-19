Build the library "$ARGUMENTS" for macOS with:
- ARM64 Release: python3 build.py --macos-sdk 12.0 --arch arm64 --build-type Release --library $ARGUMENTS --no-deps
- x86_64 Release: python3 build.py --macos-sdk 12.0 --arch x86_64 --build-type Release --library $ARGUMENTS --no-deps
Report success/failure for each.