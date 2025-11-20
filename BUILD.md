# Building Executables

## Automatic Builds (Recommended)

When you push a tag (e.g., `v1.0.0`) to GitHub, the workflow automatically builds Windows and Linux executables and creates a GitHub release.

```bash
git tag v1.0.0
git push origin v1.0.0
```

The executables will be available in the GitHub Releases page.

You can also trigger builds manually:
1. Go to Actions tab on GitHub
2. Select "Build Releases"
3. Click "Run workflow"

## Manual Build on Windows

If you want to build the .exe locally on a Windows machine:

1. **Install Python 3.10+** from python.org

2. **Install dependencies:**
   ```cmd
   pip install -r requirements.txt
   pip install pyinstaller
   ```

3. **Build the executable:**
   ```cmd
   pyinstaller cleanfilenames.spec
   ```

4. **Find the executable:**
   The `.exe` file will be in the `dist/` folder: `dist/CleanFilenames.exe`

## Manual Build on Linux

The same process works on Linux, producing a Linux executable:

```bash
pip install -r requirements.txt
pip install pyinstaller
pyinstaller cleanfilenames.spec
```

Result: `dist/CleanFilenames` (Linux binary)

## Notes

- PyInstaller builds for the platform you're running on
- The executable is self-contained and includes Python + all dependencies
- File size is ~90MB due to PySide6/Qt libraries
- No installation required - users just run the .exe
