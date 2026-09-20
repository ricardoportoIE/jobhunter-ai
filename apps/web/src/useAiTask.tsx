import { useRef } from "react";
import { useTask } from "./useTask";

type Action = (headers: Record<string, string>) => Promise<void>;
export function useAiTask(enabled = true) {
  const task = useTask();
  const last = useRef<{ action: Action; message: string } | null>(null);
  async function run(action: Action, message = "Operação concluída.") {
    last.current = { action, message };
    await task.run(() => action({}), message);
  }
  return {
    busy: task.busy,
    run,
    feedback: (
      <>
        {task.feedback}
        {task.error && (
          <button
            type="button"
            disabled={task.busy || !enabled}
            onClick={() => {
              const previous = last.current;
              if (previous)
                void task.run(
                  () =>
                    previous.action({ "Idempotency-Key": crypto.randomUUID() }),
                  previous.message,
                );
            }}
          >
            Tentar novamente após corrigir a causa
          </button>
        )}
      </>
    ),
  };
}
