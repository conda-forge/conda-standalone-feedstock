set -euxo pipefail

# patched conda files
# new files in patches need to be added here
for fname in "core/path_actions.py" "utils.py"; do
  cp conda_src/conda/${fname} $SP_DIR/conda/${fname}
done

# `base` conda might use sigtool, which ships a codesign binary that shadows Apple's one
# pyinstaller expects that one first in PATH
if [[ $target_platform = "osx-"* ]]; then
  ln -s /usr/bin/codesign "$BUILD_PREFIX/bin/codesign"
fi

# -F is to create a single file
# -s strips executables and libraries
pyinstaller conda.exe.spec
mkdir -p $PREFIX/standalone_conda
mv dist/conda.exe $PREFIX/standalone_conda
# clean up .pyc files that pyinstaller creates
rm -rf $PREFIX/lib
