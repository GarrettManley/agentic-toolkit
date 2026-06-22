import { useState, useId } from "react";
import { AnimatePresence, motion } from "motion/react";

interface Props {
  trigger: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

export function DisclosureSection({
  trigger,
  children,
  defaultOpen = false,
}: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const id = useId();
  const bodyId = `disclosure-${id}`;

  return (
    <div>
      <button
        className="drawer-trigger"
        aria-expanded={open}
        aria-controls={bodyId}
        onClick={() => setOpen((v) => !v)}
      >
        <span
          className={`drawer-arrow ${open ? "open" : ""}`}
          aria-hidden="true"
        >
          ▶
        </span>
        {trigger}
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            id={bodyId}
            className="drawer-body"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
          >
            <div style={{ paddingTop: "0.5rem" }}>{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
