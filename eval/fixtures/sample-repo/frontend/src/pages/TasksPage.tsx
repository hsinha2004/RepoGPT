import React, { useState, useEffect } from "react";
import { fetchTasks, createTask, completeTask, deleteTask, Task } from "../api/tasks";
import { TaskItem } from "../components/TaskItem";

export const TasksPage: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState("medium");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadTasks();
  }, []);

  const loadTasks = async () => {
    setLoading(true);
    try {
      const data = await fetchTasks();
      setTasks(data);
    } catch (err) {
      console.error("Failed to load tasks", err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title) return;
    try {
      const newTask = await createTask({ title, description, priority });
      setTasks((prev) => [newTask, ...prev]);
      setTitle("");
      setDescription("");
    } catch (err) {
      console.error("Failed to create task", err);
    }
  };

  const handleComplete = async (taskId: number) => {
    try {
      const updated = await completeTask(taskId);
      setTasks((prev) => prev.map((t) => (t.id === taskId ? updated : t)));
    } catch (err) {
      console.error("Failed to complete task", err);
    }
  };

  const handleDelete = async (taskId: number) => {
    try {
      await deleteTask(taskId);
      setTasks((prev) => prev.filter((t) => t.id !== taskId));
    } catch (err) {
      console.error("Failed to delete task", err);
    }
  };

  return (
    <div className="tasks-page">
      <h2>My Tasks</h2>
      <form onSubmit={handleCreate} className="create-task-form">
        <input
          type="text"
          placeholder="New task title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
        <input
          type="text"
          placeholder="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <select value={priority} onChange={(e) => setPriority(e.target.value)}>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="urgent">Urgent</option>
        </select>
        <button type="submit">Add Task</button>
      </form>

      {loading ? (
        <p>Loading tasks...</p>
      ) : (
        <div className="tasks-list">
          {tasks.map((task) => (
            <TaskItem key={task.id} task={task} onComplete={handleComplete} onDelete={handleDelete} />
          ))}
        </div>
      )}
    </div>
  );
};
