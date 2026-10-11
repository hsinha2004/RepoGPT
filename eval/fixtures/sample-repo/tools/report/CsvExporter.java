package dev.taskflow.report;

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

public class CsvExporter {

    public void exportToCsv(List<ReportGenerator.TaskSummary> tasks, Path outputPath) throws IOException {
        if (outputPath.getParent() != null) {
            Files.createDirectories(outputPath.getParent());
        }

        try (BufferedWriter writer = Files.newBufferedWriter(outputPath)) {
            writer.write("title,status,priority\n");
            for (ReportGenerator.TaskSummary task : tasks) {
                writer.write(String.format("\"%s\",\"%s\",\"%s\"\n",
                        escapeCsv(task.getTitle()),
                        escapeCsv(task.getStatus()),
                        escapeCsv(task.getPriority())));
            }
        }
    }

    private String escapeCsv(String input) {
        if (input == null) return "";
        return input.replace("\"", "\"\"");
    }
}
