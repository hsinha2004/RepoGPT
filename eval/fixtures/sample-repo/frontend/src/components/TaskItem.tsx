import React from "react";
import { Task } from "../api/tasks";

interface TaskItemProps {
  task: Task;
  onComplete: (taskId: number) => Promise<void>;
  onDelete: (taskId: number) => Promise<void>;
}

export const TaskItem: React.FC<TaskItemProps> = ({ task, onComplete, onDelete }) => {
  const handleToggle = async () => {
    if (task.status !== "completed") {
      await onComplete(task.id);
    }
  };

  return (
    <div className={`task-item ${task.status}`}>
      <div className="task-content">
        <h4>{task.title}</h4>
        {task.description && <p>{task.description}</p>}
        <span className={`priority-badge ${task.priority}`}>{task.priority}</span>
      </div>
      <div className="task-actions">
        <button onClick={handleToggle} disabled={task.status === "completed"}>
          {task.status === "completed" ? "Done" : "Complete"}
        </button>
        <button onClick={() => onDelete(task.id)} className="delete-btn">
          Delete
        </button>
      </div>
    </div>
  );
};
