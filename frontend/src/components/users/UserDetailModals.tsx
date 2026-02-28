import { Modal } from "../ui/Modal";
import { Button } from "../ui/Button";
import { Spinner } from "../ui/Spinner";
import { SortableHeader } from "../table/SortableHeader";
import { DatePicker } from "../ui/DatePicker";
import {
  formatDateTime,
  formatDuration,
  truncateText,
} from "../../utils/formatters";
import type {
  AccessLogEntry,
  PaginatedData,
  PlaylistPreview,
  SessionEntry,
} from "../../api/types";

interface SortController {
  sortBy: string;
  sortDir: string;
  toggleSort: (field: string) => void;
}

interface DateRangeProps {
  from: string;
  to: string;
  onFromChange: (value: string) => void;
  onToChange: (value: string) => void;
}

function parseDate(value: string): Date | null {
  if (!value) return null;
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return null;
  return new Date(year, month - 1, day);
}

function formatDate(value: Date | null): string {
  if (!value) return "";
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function DateRangeFilters({
  from,
  to,
  onFromChange,
  onToChange,
}: DateRangeProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
      <DatePicker
        label="From"
        selected={parseDate(from)}
        onChange={(date) => onFromChange(formatDate(date))}
        isClearable={false}
      />
      <DatePicker
        label="To"
        selected={parseDate(to)}
        onChange={(date) => onToChange(formatDate(date))}
        isClearable={false}
      />
    </div>
  );
}

export function PlaylistPreviewModal({
  open,
  onClose,
  playlist,
}: {
  open: boolean;
  onClose: () => void;
  playlist: PlaylistPreview | undefined;
}) {
  if (!open) return null;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Playlist Preview"
      maxWidth="max-w-4xl"
      footer={
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
      }
    >
      {playlist ? (
        <div className="space-y-4">
          <div className="flex flex-col gap-1 text-sm text-slate-600 sm:flex-row sm:items-center sm:justify-between">
            <span>
              Filename: <strong>{playlist.filename}</strong>
            </span>
            <span>
              Channels: <strong>{playlist.channel_count}</strong>
            </span>
          </div>
          <textarea
            readOnly
            rows={15}
            value={playlist.content}
            className="w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 font-mono text-xs text-slate-800"
          />
        </div>
      ) : (
        <div className="flex justify-center py-8">
          <Spinner />
        </div>
      )}
    </Modal>
  );
}

export function SessionsLogModal({
  open,
  onClose,
  from,
  to,
  onFromChange,
  onToChange,
  sortedSessions,
  sessions,
  sort,
}: {
  open: boolean;
  onClose: () => void;
  from: string;
  to: string;
  onFromChange: (value: string) => void;
  onToChange: (value: string) => void;
  sortedSessions: SessionEntry[];
  sessions: PaginatedData<SessionEntry> | undefined;
  sort: SortController;
}) {
  if (!open) return null;

  return (
    <Modal open={open} onClose={onClose} title="Sessions Log" maxWidth="max-w-6xl">
      <div className="space-y-4">
        <DateRangeFilters
          from={from}
          to={to}
          onFromChange={onFromChange}
          onToChange={onToChange}
        />
        <div className="max-h-[60vh] overflow-auto rounded-lg border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="sticky top-0 bg-slate-50">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-medium uppercase text-slate-500">
                  <SortableHeader
                    label="Started"
                    field="started_at"
                    sortBy={sort.sortBy}
                    sortDir={sort.sortDir}
                    onSort={sort.toggleSort}
                  />
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium uppercase text-slate-500">
                  <SortableHeader
                    label="Ended"
                    field="ended_at"
                    sortBy={sort.sortBy}
                    sortDir={sort.sortDir}
                    onSort={sort.toggleSort}
                  />
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium uppercase text-slate-500">
                  <SortableHeader
                    label="Duration"
                    field="duration"
                    sortBy={sort.sortBy}
                    sortDir={sort.sortDir}
                    onSort={sort.toggleSort}
                  />
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium uppercase text-slate-500">
                  <SortableHeader
                    label="IP Address"
                    field="ip"
                    sortBy={sort.sortBy}
                    sortDir={sort.sortDir}
                    onSort={sort.toggleSort}
                  />
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium uppercase text-slate-500">
                  <SortableHeader
                    label="Channel"
                    field="channel"
                    sortBy={sort.sortBy}
                    sortDir={sort.sortDir}
                    onSort={sort.toggleSort}
                  />
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium uppercase text-slate-500">
                  Protocol
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white">
              {sortedSessions.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500">
                    No sessions found for this period
                  </td>
                </tr>
              ) : (
                sortedSessions.map((s, i) => (
                  <tr key={`${s.started_at}-${i}`}>
                    <td className="px-3 py-2 text-sm">{formatDateTime(s.started_at)}</td>
                    <td className="px-3 py-2 text-sm">
                      {s.ended_at ? (
                        formatDateTime(s.ended_at)
                      ) : (
                        <span className="text-emerald-600">Active</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-sm">{formatDuration(s.duration)}</td>
                    <td className="px-3 py-2 font-mono text-sm">{s.ip || "-"}</td>
                    <td className="px-3 py-2 text-sm">{s.channel || "-"}</td>
                    <td
                      className="max-w-xs truncate px-3 py-2 text-sm text-slate-500"
                      title={s.user_agent || ""}
                    >
                      {truncateText(s.user_agent || "", 40) || "-"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        {sessions && sessions.pages > 1 && (
          <div className="text-sm text-slate-600">Total: {sessions.total} records</div>
        )}
      </div>
    </Modal>
  );
}

export function AccessLogModal({
  open,
  onClose,
  from,
  to,
  onFromChange,
  onToChange,
  sortedAccess,
  accessLogs,
  sort,
}: {
  open: boolean;
  onClose: () => void;
  from: string;
  to: string;
  onFromChange: (value: string) => void;
  onToChange: (value: string) => void;
  sortedAccess: AccessLogEntry[];
  accessLogs: PaginatedData<AccessLogEntry> | undefined;
  sort: SortController;
}) {
  if (!open) return null;

  return (
    <Modal open={open} onClose={onClose} title="Access Log" maxWidth="max-w-6xl">
      <div className="space-y-4">
        <DateRangeFilters
          from={from}
          to={to}
          onFromChange={onFromChange}
          onToChange={onToChange}
        />
        <div className="max-h-[60vh] overflow-auto rounded-lg border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="sticky top-0 bg-slate-50">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-medium uppercase text-slate-500">
                  <SortableHeader
                    label="Timestamp"
                    field="accessed_at"
                    sortBy={sort.sortBy}
                    sortDir={sort.sortDir}
                    onSort={sort.toggleSort}
                  />
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium uppercase text-slate-500">
                  <SortableHeader
                    label="IP Address"
                    field="ip"
                    sortBy={sort.sortBy}
                    sortDir={sort.sortDir}
                    onSort={sort.toggleSort}
                  />
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium uppercase text-slate-500">
                  <SortableHeader
                    label="Channel"
                    field="channel"
                    sortBy={sort.sortBy}
                    sortDir={sort.sortDir}
                    onSort={sort.toggleSort}
                  />
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium uppercase text-slate-500">
                  <SortableHeader
                    label="Action"
                    field="action"
                    sortBy={sort.sortBy}
                    sortDir={sort.sortDir}
                    onSort={sort.toggleSort}
                  />
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium uppercase text-slate-500">
                  Protocol
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white">
              {sortedAccess.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500">
                    No access logs found for this period
                  </td>
                </tr>
              ) : (
                sortedAccess.map((log, i) => (
                  <tr key={`${log.accessed_at}-${i}`}>
                    <td className="px-3 py-2 text-sm">{formatDateTime(log.accessed_at)}</td>
                    <td className="px-3 py-2 font-mono text-sm">{log.ip || "-"}</td>
                    <td className="px-3 py-2 text-sm">{log.channel || "-"}</td>
                    <td className="px-3 py-2 text-sm">{log.action || "-"}</td>
                    <td
                      className="max-w-xs truncate px-3 py-2 text-sm text-slate-500"
                      title={log.user_agent || ""}
                    >
                      {truncateText(log.user_agent || "", 40) || "-"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        {accessLogs && accessLogs.pages > 1 && (
          <div className="text-sm text-slate-600">Total: {accessLogs.total} records</div>
        )}
      </div>
    </Modal>
  );
}
