type WorkflowStage = "forecast" | "scenario" | "optimize" | "audit" | "sensitivity";

const stages: Array<{ id: WorkflowStage; label: string }> = [
  { id: "forecast", label: "Forecast" },
  { id: "scenario", label: "Scenario" },
  { id: "optimize", label: "Optimize" },
  { id: "audit", label: "Audit" },
  { id: "sensitivity", label: "Sensitivity" }
];

export function WorkflowRibbon({ active }: { active: WorkflowStage }) {
  return <nav className="workflow-ribbon" aria-label="Decision workflow">
    {stages.map((stage, index) => <div className={`workflow-step workflow-step-${stage.id}${stage.id === active ? " is-active" : ""}`} aria-current={stage.id === active ? "step" : undefined} key={stage.id}>
      <span className="workflow-step-index">{index + 1}</span>
      <span>{stage.label}</span>
    </div>)}
  </nav>;
}
