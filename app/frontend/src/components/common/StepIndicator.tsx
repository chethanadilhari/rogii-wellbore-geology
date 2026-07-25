interface StepDefinition {
  id: string;
  label: string;
}

interface StepIndicatorProps {
  steps: StepDefinition[];
  currentStepId: string;
  completedStepIds?: string[];
}

export function StepIndicator({
  steps,
  currentStepId,
  completedStepIds = [],
}: StepIndicatorProps) {
  return (
    <nav className="step-indicator" aria-label="Prediction workflow steps">
      {steps.map((step, index) => {
        const done = completedStepIds.includes(step.id);
        const active = step.id === currentStepId;
        const className = [
          'step-pill',
          active ? 'active' : '',
          done ? 'done' : '',
        ]
          .filter(Boolean)
          .join(' ');
        return (
          <span
            key={step.id}
            className={className}
            aria-current={active ? 'step' : undefined}
          >
            <span aria-hidden="true">{index + 1}</span>
            {step.label}
          </span>
        );
      })}
    </nav>
  );
}
