import { useCallback, useRef, type ReactNode } from "react";

interface ResizableHeaderProps {
  colKey: string;
  width?: number;
  onResize: (colKey: string, width: number) => void;
  children: ReactNode;
  className?: string;
}

export function ResizableHeader({
  colKey,
  width,
  onResize,
  children,
  className,
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
        if (newWidth > 40 && th) {
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
          onResize(colKey, th.offsetWidth);
        }
      }

      document.addEventListener("mousemove", onMouseMove);
      document.addEventListener("mouseup", onMouseUp);
    },
    [colKey, onResize]
  );

  return (
    <th
      ref={thRef}
      data-col-key={colKey}
      style={width ? { width: `${width}px` } : undefined}
      className={`px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase relative overflow-hidden text-ellipsis whitespace-nowrap border-r border-gray-200 last:border-r-0 ${className || ""}`}
    >
      {children}
      <span className="resize-handle" onMouseDown={handleMouseDown} />
    </th>
  );
}
