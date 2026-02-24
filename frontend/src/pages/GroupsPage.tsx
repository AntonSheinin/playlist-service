import { useState, useMemo } from "react";
import { useGroups, useCreateGroup, useUpdateGroup, useDeleteGroup } from "../hooks/useGroups";
import { useToast } from "../hooks/useToast";
import { useSortable } from "../hooks/useSortable";
import { useColumnResize } from "../hooks/useColumnResize";
import { Button } from "../components/ui/Button";
import { Modal } from "../components/ui/Modal";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { Spinner } from "../components/ui/Spinner";
import { EmptyState } from "../components/ui/EmptyState";
import { SortableHeader } from "../components/table/SortableHeader";
import { ResizableHeader } from "../components/table/ResizableHeader";
import type { GroupWithCount } from "../api/types";

export function GroupsPage() {
  const { data: groups, isLoading } = useGroups();
  const createGroup = useCreateGroup();
  const updateGroup = useUpdateGroup();
  const deleteGroupMut = useDeleteGroup();
  const { showToast } = useToast();
  const { sortBy, sortDir, toggleSort } = useSortable("sort_order");
  const { widths, onResize } = useColumnResize("groupsTableWidths");

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
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">Channel Groups</h1>
        <Button onClick={openAddModal}>+ Add Group</Button>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 resizable-table" style={{ width: "100%" }}>
          <thead className="bg-gray-50">
            <tr>
              <ResizableHeader colKey="name" width={widths.name} onResize={onResize}>
                <SortableHeader label="Name" field="name" sortBy={sortBy} sortDir={sortDir} onSort={toggleSort} />
              </ResizableHeader>
              <ResizableHeader colKey="channels" width={widths.channels} onResize={onResize} className="w-32">
                <SortableHeader label="Channels" field="channel_count" sortBy={sortBy} sortDir={sortDir} onSort={toggleSort} />
              </ResizableHeader>
              <ResizableHeader colKey="actions" width={widths.actions} onResize={onResize} className="w-28">
                Actions
              </ResizableHeader>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sortedGroups.length === 0 ? (
              <EmptyState message="No groups yet" colSpan={3} />
            ) : (
              sortedGroups.map((group) => (
                <tr key={group.id}>
                  <td className="px-4 py-3">
                    <span className="font-medium">{group.name}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-gray-600">{group.channel_count}</span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center space-x-1">
                      <Button size="sm" onClick={() => openEditModal(group)}>Edit</Button>
                      <Button size="sm" variant="danger" onClick={() => setDeleteTarget(group)}>Delete</Button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Add/Edit Modal */}
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
          <div>
            <label className="block text-sm font-medium text-gray-700">Group Name</label>
            <input
              type="text"
              value={groupName}
              onChange={(e) => setGroupName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSave()}
              autoFocus
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </Modal>
      )}

      {/* Delete Confirmation */}
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
