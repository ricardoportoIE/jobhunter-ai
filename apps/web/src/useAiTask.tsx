import { t } from "./i18n";
import { useRef, useState } from "react";
import { useTask } from "./useTask";
type Action = (headers: Record<string, string>) => Promise<void>;
export function useAiTask(enabled = true, context = "") {
  const task = useTask();
  const [operationContext, setOperationContext] = useState(context);
  const last = useRef<{
    action: Action;
    message: string;
    context: string;
  } | null>(null);
  async function run(action: Action, message = t("Operation completed.")) {
    last.current = { action, message, context };
    setOperationContext(context);
    await task.run(() => action({}), message);
  }
  return {
    busy: task.busy,
    run,
    feedback: (
      <>
        {task.feedback}
        {task.error && operationContext === context && (
          <button
            type="button"
            disabled={task.busy || !enabled}
            onClick={() => {
              const previous = last.current;
              if (previous && previous.context === context)
                void task.run(
                  () =>
                    previous.action({ "Idempotency-Key": crypto.randomUUID() }),
                  previous.message,
                );
            }}
          >
            {t("Try again after fixing the cause")}
          </button>
        )}
      </>
    ),
  };
}
