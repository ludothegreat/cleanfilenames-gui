# Building Executables

## Cross-Compile Windows .exe on Linux (Recommended)

Since PyInstaller cannot cross-compile natively, you can use Docker with Wine to build Windows executables from Linux:

1. **Pull the Docker image:**
   ```bash
   docker pull batonogov/pyinstaller-windows
   ```

2. **Build the Windows executable:**
   ```bash
   docker run --rm -v "$(pwd):/src" batonogov/pyinstaller-windows \
     "pip install -r requirements.txt && pyinstaller --clean cleanfilenames.spec"
   ```

3. **Fix file ownership (files are created as root):**
   ```bash
   sudo chown -R $USER:$USER dist/
   ```

4. **Find the executable:**
   - Location: `dist/CleanFilenames.exe`
   - Size: ~25MB (with UPX compression)
   - Type: PE32+ executable for Windows (64-bit GUI)

**How it works:**
- The Docker container runs Linux with Wine installed
- Wine provides Windows API compatibility on Linux
- PyInstaller (Windows version) runs through Wine to create genuine Windows executables
- No actual Windows installation required - purely command-line toolchain
- The resulting `.exe` is a real Windows executable that runs on Windows computers

**Note:** You cannot run or test the GUI through this container - it's build-only. To test the `.exe`, you need:
- An actual Windows computer
- A Windows VM (VirtualBox, QEMU, etc.)
- Wine on your Linux desktop: `wine dist/CleanFilenames.exe`

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
