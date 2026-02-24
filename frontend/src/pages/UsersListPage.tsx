import { useState } from "react";
import { Link } from "react-router-dom";
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
import { SortableHeader } from "../components/table/SortableHeader";
import { ResizableHeader } from "../components/table/ResizableHeader";
import type { UserListItem } from "../api/types";

export function UsersListPage() {
  const { showToast } = useToast();
  const { sortBy, sortDir, toggleSort } = useSortable("name");
  const { widths, onResize } = useColumnResize("usersTableWidths");

  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [tariffFilter, setTariffFilter] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const search = useDebounce(searchInput);

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
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">Users</h1>
        <Link to="/users/new">
          <Button>+ Add User</Button>
        </Link>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">All Status</option>
              <option value="enabled">Enabled</option>
              <option value="disabled">Disabled</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Tariff</label>
            <select
              value={tariffFilter}
              onChange={(e) => { setTariffFilter(e.target.value); setPage(1); }}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">All Tariffs</option>
              {(tariffs || []).map((t) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </div>
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700">Search</label>
            <input
              type="text"
              value={searchInput}
              onChange={(e) => { setSearchInput(e.target.value); setPage(1); }}
              placeholder="Search by name or agreement number..."
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Users table */}
      <div className="bg-white rounded-lg shadow overflow-hidden overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 resizable-table" style={{ width: "100%" }}>
          <thead className="bg-gray-50">
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
              <ResizableHeader colKey="actions" width={widths.actions} onResize={onResize} className="w-24">
                Actions
              </ResizableHeader>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {users.length === 0 ? (
              <EmptyState message="No users found" colSpan={6} />
            ) : (
              users.map((user) => (
                <tr key={user.id} className={user.status === "disabled" ? "bg-gray-50" : ""}>
                  <td className="px-4 py-3">
                    <div className="font-medium">{user.last_name} {user.first_name}</div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-sm text-gray-600">{user.agreement_number}</span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap">
                      {user.tariffs && user.tariffs.length > 0
                        ? user.tariffs.map((t) => (
                            <Badge key={t.id} variant="blue" className="mr-1 mb-1">
                              {t.name}
                            </Badge>
                          ))
                        : <span className="text-xs text-gray-400">-</span>
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
                    <div className="flex items-center space-x-1">
                      <Link to={`/users/${user.id}`}>
                        <Button size="sm">Edit</Button>
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

        <Pagination
          page={data?.page || 1}
          pages={totalPages}
          total={total}
          onPageChange={setPage}
          label="users"
        />
      </div>

      {/* Delete Confirmation */}
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
