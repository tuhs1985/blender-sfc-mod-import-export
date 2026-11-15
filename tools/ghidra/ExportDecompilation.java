// Export Ghidra's C-like decompilation for offline investigation.
// @category SFC
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import java.io.File;
import java.io.PrintWriter;

public class ExportDecompilation extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 1) throw new IllegalArgumentException("Provide an output directory");
        File dir = new File(args[0]);
        if (!dir.isDirectory() && !dir.mkdirs()) throw new Exception("Cannot create " + dir);
        File output = new File(dir, currentProgram.getName() + ".c.txt");
        DecompInterface decompiler = new DecompInterface();
        if (!decompiler.openProgram(currentProgram)) throw new Exception("Cannot open program");
        try (PrintWriter writer = new PrintWriter(output, "UTF-8")) {
            FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
            while (functions.hasNext() && !monitor.isCancelled()) {
                Function function = functions.next();
                writer.println("\n/* " + function.getEntryPoint() + " " + function.getName() + " */");
                DecompileResults result = decompiler.decompileFunction(function, 60, monitor);
                if (result.decompileCompleted()) writer.println(result.getDecompiledFunction().getC());
                else writer.println("/* Decompilation failed: " + result.getErrorMessage() + " */");
            }
        } finally {
            decompiler.dispose();
        }
        println("Wrote " + output);
    }
}
