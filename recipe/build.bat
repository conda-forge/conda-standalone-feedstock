@ECHO on

SET "PYINSTALLER_CONDARC_DIR=%RECIPE_DIR%"
FOR /F "tokens=*" %%g IN ('python -c "import site; print(site.getsitepackages()[1])"') do (SET SP_DIR=%%g)

python "%SRC_DIR%\recipe\copy_patches.py" ^
  --patch-source "%SRC_DIR%\src\conda_patches" ^
  --site-packages "%SP_DIR%" ^
  --conda-source conda_src || goto :error

:: we need these for noarch packages with entry points to work on windows
COPY "conda_src\conda\shell\cli-%ARCH%.exe" entry_point_base.exe || goto :error

pyinstaller --clean --log-level=DEBUG src\conda.exe.spec || goto :error
MKDIR "%PREFIX%\standalone_conda" || goto :error
MOVE dist\conda.exe "%PREFIX%\standalone_conda\conda.exe" || goto :error

:: Collect licenses
python src\licenses.py ^
  --prefix "%BUILD_PREFIX%" ^
  --include-text ^
  --text-errors replace ^
  --output "%SRC_DIR%\3rd-party-licenses.json" || goto :error

RD /s /q "%PREFIX%\lib" || goto :error

goto :EOF

:error
set "exitcode=%errorlevel%"
echo Failed with error #%exitcode%.
exit /b %exitcode%
