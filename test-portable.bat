@echo off
:: Test script for portable AtlasVibe build

echo Building portable version...
call pnpm run electron-package:windows-portable

echo.
echo Build complete. Testing launch...
echo.

:: Test the portable version
cd dist-portable
if exist "AtlasVibe Portable*.exe" (
    echo Found portable executable. Extracting...
    :: The portable exe is self-extracting
    for %%f in ("AtlasVibe Portable*.exe") do (
        echo Running: %%f
        start /wait "" "%%f"
    )
) else (
    echo ERROR: Portable build not found!
)

pause
