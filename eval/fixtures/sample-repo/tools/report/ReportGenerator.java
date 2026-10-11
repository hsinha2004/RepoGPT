package dev.taskflow.report;

import java.io.IOException;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

public class ReportGenerator {

    public static class TaskSummary {
        private final String title;
        private final String status;
        private final String priority;

        public TaskSummary(String title, String status, String priority) {
            this.title = title;
            this.status = status;
            this.priority = priority;
        }

        public String getTitle() { return title; }
        public String getStatus() { return status; }
        public String getPriority() { return priority; }
    }

    public static void main(String[] args) {
        System.out.println("Generating TaskFlow completion summary report...");
        List<TaskSummary> summaries = new ArrayList<>();
        summaries.add(new TaskSummary("Set up Database", "completed", "high"));
        summaries.add(new TaskSummary("Implement JWT Auth", "completed", "high"));
        summaries.add(new TaskSummary("Build React UI", "pending", "medium"));

        CsvExporter exporter = new CsvExporter();
        try {
            exporter.exportToCsv(summaries, Path.of("reports/tasks_report.csv"));
            System.out.println("Report successfully written to reports/tasks_report.csv");
        } catch (IOException e) {
            System.err.println("Failed to write report: " + e.getMessage());
        }
    }
}
