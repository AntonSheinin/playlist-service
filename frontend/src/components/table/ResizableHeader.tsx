import { useCallback, useRef, type ReactNode } from "react";
import { cn } from "../../lib/utils";

interface ResizableHeaderProps {
  colKey: string;
  width?: number;
  onResize: (colKey: string, width: number) => void;
  children: ReactNode;
  className?: string;
  minWidth?: number;
}

export function ResizableHeader({
  colKey,
  width,
  onResize,
  children,
  className,
  minWidth = 56,
}: ResizableHeaderProps) {
  const thRef = useRef<HTMLTableCellElement>(null);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();

      const th = thRef.current;
      if (!th) return;

      const startX = e.pageX;
      const startWidth = th.offsetWidth;
      const handle = e.currentTarget as HTMLElement;

      handle.classList.add("resizing");
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";

      function onMouseMove(ev: MouseEvent) {
        const newWidth = startWidth + (ev.pageX - startX);
        if (newWidth > minWidth && th) {
          th.style.width = `${newWidth}px`;
        }
      }

      function onMouseUp() {
        handle.classList.remove("resizing");
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
        document.removeEventListener("mousemove", onMouseMove);
        document.removeEventListener("mouseup", onMouseUp);

        if (th) {
          onResize(colKey, Math.max(th.offsetWidth, minWidth));
        }
      }

      document.addEventListener("mousemove", onMouseMove);
      document.addEventListener("mouseup", onMouseUp);
    },
    [colKey, minWidth, onResize]
  );

  return (
    <th
      ref={thRef}
      data-col-key={colKey}
      scope="col"
      className={cn(
        "relative border-r border-border bg-muted px-3 py-2 text-left text-xs font-semibold uppercase text-muted-foreground",
        className
      )}
      style={width ? { width: `${Math.max(width, minWidth)}px` } : { minWidth: `${minWidth}px` }}
    >
      {children}
      <span className="resize-handle" onMouseDown={handleMouseDown} />
    </th>
  );
}
