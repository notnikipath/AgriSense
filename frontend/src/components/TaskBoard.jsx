import React from "react";

export function TaskBoard({ tasks }) {
  if (!tasks?.length) {
    return <div className="empty-board">No planned operations yet. Create an irrigation or fertilization task.</div>;
  }

  return (
    <section className="route-lane">
      {tasks.map((task) => (
        <article className="route-stop" key={task.task_id}>
          <p className="lesson-type">{task.work_type}</p>
          <h4>{task.assignee || "Unassigned"}</h4>
          <div className="lesson-meta">
            <span>{new Date(task.planned_start).toLocaleString()}</span>
            <span>{task.machinery || "Machinery TBD"}</span>
          </div>
        </article>
      ))}
    </section>
  );
}
