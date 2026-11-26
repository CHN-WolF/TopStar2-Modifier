@echo off
setlocal EnableExtensions

set "SCRIPT="
for /d %%D in ("%~dp0*") do if exist "%%D\modifier.py" set "SCRIPT=%%D\modifier.py"
if not defined SCRIPT (
  echo modifier.py was not found.
  pause
  exit /b 1
)

call :FIND_PYTHON

if not defined PYW (
  set "INSTALLER="
  for %%F in ("%~dp0³ÌÐò\python-*.exe") do if not defined INSTALLER set "INSTALLER=%%~F"
  if not defined INSTALLER (
    for %%F in ("%~dp0python-*.exe") do if not defined INSTALLER set "INSTALLER=%%~F"
  )
  if defined INSTALLER (
    echo Python was not found. Installing Python automatically, please wait...
    start /wait "" "%INSTALLER%" /passive InstallAllUsers=0 PrependPath=1 Include_tcltk=1 Include_test=0
    call :FIND_PYTHON
  )
)

if not defined PYW (
  echo Python was not found. Please install Python 3 from https://www.python.org/downloads/ and check "Add python.exe to PATH".
  pause
  exit /b 1
)

start "" "%PYW%" "%SCRIPT%"
exit /b 0

:FIND_PYTHON
set "PYW="
for %%N in (pythonw.exe python.exe) do (
  if not defined PYW (
    for /f "delims=" %%I in ('where %%N 2^>nul') do (
      echo "%%I" | find /I "WindowsApps" >nul
      if errorlevel 1 if not defined PYW if exist "%%~I" set "PYW=%%~I"
    )
  )
)
if not defined PYW (
  for %%L in (pyw.exe py.exe) do (
    if not defined PYW (
      for /f "delims=" %%P in ('%%L -3 -c "import sys; print(sys.executable)" 2^>nul') do (
        if exist "%%~P" set "PYW=%%~P"
      )
    )
  )
)
if not defined PYW (
  for %%E in (pythonw.exe python.exe) do (
    if not defined PYW (
      for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*" "%ProgramFiles%\Python3*" "%SystemDrive%\Python3*" "%LOCALAPPDATA%\Python\pythoncore-*") do (
        if not defined PYW if exist "%%~D\%%E" set "PYW=%%~D\%%E"
      )
    )
  )
)
if not defined PYW if exist "%LOCALAPPDATA%\Python\bin\pythonw.exe" set "PYW=%LOCALAPPDATA%\Python\bin\pythonw.exe"
if not defined PYW if exist "%LOCALAPPDATA%\Python\bin\python.exe" set "PYW=%LOCALAPPDATA%\Python\bin\python.exe"
exit /b 0
