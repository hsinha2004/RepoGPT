import { apiFetch } from "./client";

export interface Task {
  id: number;
  user_id: number;
  title: string;
  description?: string;
  status: "pending" | "completed";
  priority: "low" | "medium" | "high" | "urgent";
  due_date?: string;
  created_at: string;
}

export interface CreateTaskPayload {
  title: string;
  description?: string;
  priority?: string;
  due_date?: string;
}

export async function fetchTasks(): Promise<Task[]> {
  return apiFetch<Task[]>("/tasks");
}

export async function createTask(payload: CreateTaskPayload): Promise<Task> {
  return apiFetch<Task>("/tasks", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function completeTask(taskId: number): Promise<Task> {
  return apiFetch<Task>(`/tasks/${taskId}/complete`, {
    method: "PATCH",
  });
}

export async function deleteTask(taskId: number): Promise<void> {
  return apiFetch<void>(`/tasks/${taskId}`, {
    method: "DELETE",
  });
}
