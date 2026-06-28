import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Pencil, Trash2 } from "lucide-react";
import { useGroups, useCreateGroup, useUpdateGroup, useDeleteGroup } from "../hooks/useGroups";
import { useToast } from "../hooks/useToast";
import { useSortable } from "../hooks/useSortable";
import { useColumnResize } from "../hooks/useColumnResize";
import { Button } from "../components/ui/Button";
import { Modal } from "../components/ui/Modal";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { Spinner } from "../components/ui/Spinner";
import { EmptyState } from "../components/ui/EmptyState";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { PageHeader } from "../components/ui/PageHeader";
import { Pagination } from "../components/ui/Pagination";
import { SortableHeader } from "../components/table/SortableHeader";
import { ResizableHeader } from "../components/table/ResizableHeader";
import type { GroupWithCount } from "../api/types";

function parsePositiveInt(value: string | null, fallback: number) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

export function GroupsPage() {
  const { data: groups, isLoading } = useGroups();
  const createGroup = useCreateGroup();
  const updateGroup = useUpdateGroup();
  const deleteGroupMut = useDeleteGroup();
  const { showToast } = useToast();
  const { sortBy, sortDir, toggleSort } = useSortable("sort_order");
  const { widths, onResize } = useColumnResize("groupsTableWidths");
  const [searchParams, setSearchParams] = useSearchParams();

  const page = parsePositiveInt(searchParams.get("page"), 1);
  const perPage = parsePositiveInt(searchParams.get("perPage"), 20);

  const [modalOpen, setModalOpen] = useState(false);
  const [editingGroup, setEditingGroup] = useState<GroupWithCount | null>(null);
  const [groupName, setGroupName] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<GroupWithCount | null>(null);

  const sortedGroups = useMemo(() => {
    if (!groups) return [];
    return [...groups].sort((a, b) => {
      const dir = sortDir === "asc" ? 1 : -1;
      if (sortBy === "name") return dir * a.name.localeCompare(b.name);
      if (sortBy === "channel_count") return dir * (a.channel_count - b.channel_count);
      return dir * ((a.sort_order ?? 0) - (b.sort_order ?? 0));
    });
  }, [groups, sortBy, sortDir]);

  const totalPages = Math.max(1, Math.ceil(sortedGroups.length / perPage));
  const currentPage = Math.min(page, totalPages);
  const pagedGroups = useMemo(
    () => sortedGroups.slice((currentPage - 1) * perPage, currentPage * perPage),
    [currentPage, perPage, sortedGroups],
  );

  function updateParams(patch: Record<string, string | undefined>) {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(patch)) {
      if (!value) next.delete(key);
      else next.set(key, value);
    }
    setSearchParams(next);
  }

  function openAddModal() {
    setEditingGroup(null);
    setGroupName("");
    setModalOpen(true);
  }

  function openEditModal(group: GroupWithCount) {
    setEditingGroup(group);
    setGroupName(group.name);
    setModalOpen(true);
  }

  async function handleSave() {
    const name = groupName.trim();
    if (!name) {
      showToast("Please enter a group name", "error");
      return;
    }

    try {
      if (editingGroup) {
        await updateGroup.mutateAsync({ id: editingGroup.id, data: { name } });
        showToast("Group updated", "success");
      } else {
        await createGroup.mutateAsync({ name });
        showToast("Group created", "success");
      }
      setModalOpen(false);
    } catch {
      showToast("Failed to save group", "error");
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    try {
      await deleteGroupMut.mutateAsync(deleteTarget.id);
      showToast("Group deleted", "success");
      setDeleteTarget(null);
    } catch {
      showToast("Failed to delete group", "error");
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
        title="Channel Groups"
        description="Create and maintain channel grouping used across channel assignments."
        actions={<Button onClick={openAddModal}>+ Add Group</Button>}
      />

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="resizable-table min-w-full divide-y divide-border" style={{ width: "100%" }}>
            <thead className="bg-muted">
            <tr>
              <ResizableHeader colKey="name" width={widths.name} onResize={onResize}>
                <SortableHeader label="Name" field="name" sortBy={sortBy} sortDir={sortDir} onSort={toggleSort} />
              </ResizableHeader>
              <ResizableHeader colKey="channels" width={widths.channels} onResize={onResize} className="w-32">
                <SortableHeader label="Channels" field="channel_count" sortBy={sortBy} sortDir={sortDir} onSort={toggleSort} />
              </ResizableHeader>
              <ResizableHeader colKey="actions" width={widths.actions} onResize={onResize} className="w-40" minWidth={160}>
                Actions
              </ResizableHeader>
            </tr>
          </thead>
            <tbody className="divide-y divide-border bg-card">
            {sortedGroups.length === 0 ? (
              <EmptyState message="No groups yet" colSpan={3} />
            ) : (
              pagedGroups.map((group) => (
                <tr key={group.id}>
                  <td className="px-4 py-3">
                    <span className="font-medium">{group.name}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-muted-foreground">{group.channel_count}</span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        className="h-8 w-8 px-0"
                        onClick={() => openEditModal(group)}
                        aria-label={`Edit group ${group.name}`}
                        title="Edit"
                      >
                        <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
                      </Button>
                      <Button
                        size="sm"
                        variant="danger"
                        className="h-8 w-8 px-0"
                        onClick={() => setDeleteTarget(group)}
                        aria-label={`Delete group ${group.name}`}
                        title="Delete"
                      >
                        <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
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
          page={currentPage}
          pages={totalPages}
          total={sortedGroups.length}
          onPageChange={(nextPage) => updateParams({ page: String(nextPage) })}
          perPage={perPage}
          onPerPageChange={(nextPerPage) => {
            updateParams({ perPage: String(nextPerPage), page: "1" });
          }}
          label="groups"
        />
      </Card>

      {modalOpen && (
        <Modal
          open={modalOpen}
          onClose={() => setModalOpen(false)}
          title={editingGroup ? "Edit Group" : "Add Group"}
          footer={
            <>
              <Button variant="secondary" onClick={() => setModalOpen(false)}>Cancel</Button>
              <Button onClick={handleSave} loading={createGroup.isPending || updateGroup.isPending}>Save</Button>
            </>
          }
        >
          <Input
            label="Group Name"
              type="text"
              value={groupName}
              onChange={(e) => setGroupName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSave()}
              autoFocus
          />
        </Modal>
      )}

      {!!deleteTarget && (
        <ConfirmDialog
          open={!!deleteTarget}
          onClose={() => setDeleteTarget(null)}
          onConfirm={handleDelete}
          title="Delete Group"
          message={`Are you sure you want to delete "${deleteTarget?.name}"?`}
          details={
            deleteTarget && deleteTarget.channel_count > 0
              ? `This group has ${deleteTarget.channel_count} channels. They will be unassigned.`
              : "This group has no channels."
          }
          loading={deleteGroupMut.isPending}
        />
      )}
    </div>
  );
}
