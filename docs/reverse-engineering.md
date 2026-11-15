# Reverse engineering the original plugins

The supplied R3 and R4 importer/exporter files are 32-bit x86 Windows PE binaries. Ghidra 12.2 successfully analyzed all four and exported C-like listings. These are reconstructed pseudocode, not the original C++ source: names, types, class layouts and control flow can be incomplete or wrong. The 3ds Max SDK dependencies were not present during analysis.

The local Ghidra installation is at `C:\AI\Projects\tools\ghidra\ghidra_12.2_PUBLIC`. The Ghidra project and decompiled listings are under `output/ghidra-project/` and `output/decompiled/`; output is ignored by Git. Original binaries and listings are not committed.

## Reproduce

Install an official [Ghidra release](https://github.com/NationalSecurityAgency/ghidra/releases) and a compatible JDK. From the repository in PowerShell, adapt the paths and run once per input file:

```powershell
$env:JAVA_HOME = 'C:\path\to\jdk'
$env:APPDATA = "$PWD\output\appdata"
New-Item -ItemType Directory -Force output\ghidra-project, output\decompiled | Out-Null
& 'C:\path\to\ghidra\support\analyzeHeadless.bat' `
  "$PWD\output\ghidra-project" SFC -import 'C:\path\to\plugin.dle' `
  -scriptPath "$PWD\tools\ghidra" `
  -postScript ExportDecompilation.java "$PWD\output\decompiled" -overwrite
```

The script exports every function Ghidra identifies, including a comment with its address. Open the saved project in Ghidra for disassembly, references, data, and renaming. See the [official headless documentation](https://github.com/NationalSecurityAgency/ghidra/blob/master/Ghidra/RuntimeScripts/support/analyzeHeadlessREADME.md) for options.

## Initial observations

- The R4 exporter listing contains a file-writing function at `10002f90`. It writes a main chunk, header fields and additional chunks using `fwrite`.
- The chunk helper at `10001e10` writes a four-byte tag and a placeholder length. The helper at `10001e70` replaces that length with the payload size and pads the file to a four-byte boundary. Ghidra's inferred parameter type for the tag is unreliable; inspect the assembly when interpreting it.
- A local `Planet_test.mod` begins with ASCII `MDLS`, followed by bytes `e0 86 11 00`, and contains `STRS` at offset 44. This is one example, not yet a general format specification.
- The exporter writes `0x200` in the main header; its meaning and version compatibility need verification against more files and the importer.

Next, identify and label the read/write routines and chunk structures, compare them with multiple known MOD files, and build tests from authorized fixtures. Do not assume the R3/R4 SFC2 tools support every SFC version.
