import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useUsers, useUpdateUser, useDeleteUser } from "../hooks/useUsers";
import { useLookupTariffs } from "../hooks/useLookup";
import { useToast } from "../hooks/useToast";
import { useDebounce } from "../hooks/useDebounce";
import { useSortable } from "../hooks/useSortable";
import { useColumnResize } from "../hooks/useColumnResize";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { Spinner } from "../components/ui/Spinner";
import { EmptyState } from "../components/ui/EmptyState";
import { Pagination } from "../components/ui/Pagination";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { Input } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { Card } from "../components/ui/Card";
import { FilterBar } from "../components/ui/FilterBar";
import { PageHeader } from "../components/ui/PageHeader";
import { SortableHeader } from "../components/table/SortableHeader";
import { ResizableHeader } from "../components/table/ResizableHeader";
import type { UserListItem } from "../api/types";

function parsePage(value: string | null): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 1;
}

export function UsersListPage() {
  const { showToast } = useToast();
  const { sortBy, sortDir, toggleSort } = useSortable("name");
  const { widths, onResize } = useColumnResize("usersTableWidths");
  const [searchParams, setSearchParams] = useSearchParams();

  const page = parsePage(searchParams.get("page"));
  const statusFilter = searchParams.get("status") ?? "";
  const tariffFilter = searchParams.get("tariff") ?? "";
  const urlSearch = searchParams.get("search") ?? "";

  const [searchInput, setSearchInput] = useState(urlSearch);
  const search = useDebounce(searchInput);

  useEffect(() => {
    setSearchInput(urlSearch);
  }, [urlSearch]);

  function updateFilters(patch: Record<string, string | undefined>) {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(patch)) {
      if (!value) {
        next.delete(key);
      } else {
        next.set(key, value);
      }
    }
    setSearchParams(next);
  }

  useEffect(() => {
    const trimmed = search.trim();
    if (trimmed === urlSearch) return;
    const next = new URLSearchParams(searchParams);
    if (trimmed) {
      next.set("search", trimmed);
    } else {
      next.delete("search");
    }
    next.set("page", "1");
    setSearchParams(next);
  }, [search, searchParams, setSearchParams, urlSearch]);

  const { data, isLoading } = useUsers({
    page,
    per_page: 20,
    sort_by: sortBy,
    sort_dir: sortDir,
    status: statusFilter || undefined,
    tariff_id: tariffFilter ? Number(tariffFilter) : undefined,
    search: search || undefined,
  });

  const { data: tariffs } = useLookupTariffs();
  const updateUser = useUpdateUser();
  const deleteUserMut = useDeleteUser();

  const [deleteTarget, setDeleteTarget] = useState<UserListItem | null>(null);

  const users = data?.items || [];
  const totalPages = data?.pages || 0;
  const total = data?.total || 0;

  async function handleToggleStatus(user: UserListItem) {
    const nextStatus = user.status === "enabled" ? "disabled" : "enabled";
    try {
      await updateUser.mutateAsync({
        id: user.id,
        data: { status: nextStatus },
      });
      showToast(`Status set to ${nextStatus}`, "success");
    } catch {
      showToast("Failed to update status", "error");
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    try {
      await deleteUserMut.mutateAsync(deleteTarget.id);
      showToast("User deleted", "success");
      setDeleteTarget(null);
    } catch {
      showToast("Failed to delete user", "error");
    }
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Users"
        description="Manage users, status, and tariff assignments."
        actions={
          <Link to="/users/new">
            <Button>+ Add User</Button>
          </Link>
        }
      />

      <FilterBar>
        <Select
          label="Status"
          value={statusFilter}
          onChange={(e) =>
            updateFilters({ status: e.target.value || undefined, page: "1" })
          }
        >
          <option value="">All Status</option>
          <option value="enabled">Enabled</option>
          <option value="disabled">Disabled</option>
        </Select>

        <Select
          label="Tariff"
          value={tariffFilter}
          onChange={(e) =>
            updateFilters({ tariff: e.target.value || undefined, page: "1" })
          }
        >
          <option value="">All Tariffs</option>
          {(tariffs || []).map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </Select>

        <div className="md:col-span-2">
          <Input
            label="Search"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search by name or agreement number..."
          />
        </div>
      </FilterBar>

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table
            className="resizable-table min-w-full divide-y divide-slate-200"
            style={{ width: "100%" }}
          >
            <thead className="bg-slate-50">
            <tr>
              <ResizableHeader colKey="name" width={widths.name} onResize={onResize}>
                <SortableHeader label="Name" field="name" sortBy={sortBy} sortDir={sortDir} onSort={toggleSort} />
              </ResizableHeader>
              <ResizableHeader colKey="agreement" width={widths.agreement} onResize={onResize}>
                <SortableHeader label="Agreement" field="agreement_number" sortBy={sortBy} sortDir={sortDir} onSort={toggleSort} />
              </ResizableHeader>
              <ResizableHeader colKey="tariffs" width={widths.tariffs} onResize={onResize}>
                Tariffs
              </ResizableHeader>
              <ResizableHeader colKey="sessions" width={widths.sessions} onResize={onResize} className="w-24">
                <SortableHeader label="Sessions" field="max_sessions" sortBy={sortBy} sortDir={sortDir} onSort={toggleSort} />
              </ResizableHeader>
              <ResizableHeader colKey="status" width={widths.status} onResize={onResize} className="w-24">
                <SortableHeader label="Status" field="status" sortBy={sortBy} sortDir={sortDir} onSort={toggleSort} />
              </ResizableHeader>
              <ResizableHeader colKey="actions" width={widths.actions} onResize={onResize} className="w-40" minWidth={160}>
                Actions
              </ResizableHeader>
            </tr>
          </thead>
            <tbody className="divide-y divide-slate-200 bg-white">
            {users.length === 0 ? (
              <EmptyState message="No users found" colSpan={6} />
            ) : (
              users.map((user) => (
                <tr
                  key={user.id}
                  className={user.status === "disabled" ? "bg-slate-50/60" : ""}
                >
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900">
                      {user.last_name} {user.first_name}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-sm text-slate-600">{user.agreement_number}</span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap">
                      {user.tariffs && user.tariffs.length > 0
                        ? user.tariffs.map((t) => (
                            <Badge key={t.id} variant="blue" className="mr-1 mb-1">
                              {t.name}
                            </Badge>
                          ))
                        : <span className="text-xs text-slate-400">-</span>
                      }
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-sm">{user.max_sessions}</span>
                  </td>
                  <td className="px-4 py-3">
                    <Badge
                      variant={user.status === "enabled" ? "green" : "red"}
                      onClick={() => handleToggleStatus(user)}
                    >
                      {user.status}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      <Link to={`/users/${user.id}`}>
                        <Button size="sm" variant="secondary">Edit</Button>
                      </Link>
                      <Button size="sm" variant="danger" onClick={() => setDeleteTarget(user)}>
                        Delete
                      </Button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
          </table>
        </div>

        <Pagination
          page={data?.page || 1}
          pages={totalPages}
          total={total}
          onPageChange={(nextPage) => updateFilters({ page: String(nextPage) })}
          label="users"
        />
      </Card>

      {!!deleteTarget && (
        <ConfirmDialog
          open={!!deleteTarget}
          onClose={() => setDeleteTarget(null)}
          onConfirm={handleDelete}
          title="Delete User"
          message={`Are you sure you want to delete "${deleteTarget ? `${deleteTarget.last_name} ${deleteTarget.first_name}` : ""}"?`}
          details="This action cannot be undone. The user will be removed from the Auth Service."
          loading={deleteUserMut.isPending}
        />
      )}
    </div>
  );
}
