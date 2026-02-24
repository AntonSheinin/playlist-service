import { useState, useMemo, useCallback, useRef, useEffect } from "react";
import type { MultiValue } from "react-select";
import ReactSelect from "react-select";
import {
  useChannels,
  useBulkUpdateChannels,
  useDeleteChannel,
  useUpdateChannelGroups,
  useUpdateChannelPackages,
  useSyncChannels,
  useCascadeInfo,
  useUploadLogo,
  useUploadLogoByUrl,
  useRemoveLogo,
} from "../hooks/useChannels";
import { useLookupGroups, useLookupPackages } from "../hooks/useLookup";
import { useToast } from "../hooks/useToast";
import { useDebounce } from "../hooks/useDebounce";
import { useSortable } from "../hooks/useSortable";
import { useColumnResize } from "../hooks/useColumnResize";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { Modal } from "../components/ui/Modal";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { Spinner } from "../components/ui/Spinner";
import { EmptyState } from "../components/ui/EmptyState";
import { Pagination } from "../components/ui/Pagination";
import { SortableHeader } from "../components/table/SortableHeader";
import { ResizableHeader } from "../components/table/ResizableHeader";
import type { ChannelResponse, ChannelBulkUpdateItem } from "../api/types";

interface PendingChange {
  id: number;
  tvg_id?: string;
  tvg_logo?: string;
  channel_number?: number | null;
}

export function ChannelsPage() {
  const { showToast } = useToast();
  const { sortBy, sortDir, toggleSort } = useSortable("channel_number");
  const { widths, onResize } = useColumnResize("channelsTableWidths");

  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [groupFilter, setGroupFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const search = useDebounce(searchInput);

  const { data, isLoading } = useChannels({
    page,
    per_page: perPage,
    sort_by: sortBy,
    sort_dir: sortDir,
    group_id: groupFilter ? Number(groupFilter) : undefined,
    sync_status: statusFilter || undefined,
    search: search || undefined,
  });

  const { data: groups } = useLookupGroups();
  const { data: packages } = useLookupPackages();

  // Mutations
  const bulkUpdate = useBulkUpdateChannels();
  const deleteChannelMut = useDeleteChannel();
  const updateGroups = useUpdateChannelGroups();
  const updatePackages = useUpdateChannelPackages();
  const syncMut = useSyncChannels();
  const uploadLogoMut = useUploadLogo();
  const uploadLogoUrlMut = useUploadLogoByUrl();
  const removeLogoMut = useRemoveLogo();

  // Pending changes for inline editing
  const [pendingChanges, setPendingChanges] = useState<Record<number, PendingChange>>({});

  // Delete modal
  const [deleteTarget, setDeleteTarget] = useState<ChannelResponse | null>(null);
  const { data: cascadeInfo } = useCascadeInfo(deleteTarget?.id ?? null);

  // Logo modal
  const [logoChannel, setLogoChannel] = useState<ChannelResponse | null>(null);
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [logoFilePreview, setLogoFilePreview] = useState("");
  const [logoUrl, setLogoUrl] = useState("");
  const [logoRemovalMode, setLogoRemovalMode] = useState<"db" | "delete" | null>(null);
  const logoFileRef = useRef<HTMLInputElement>(null);

  // Edit modal
  const [editChannel, setEditChannel] = useState<ChannelResponse | null>(null);
  const [editNumber, setEditNumber] = useState("");
  const [editTvgId, setEditTvgId] = useState("");
  const [editGroupIds, setEditGroupIds] = useState<number[]>([]);
  const editLogoFileRef = useRef<HTMLInputElement>(null);
  const [editLogoFile, setEditLogoFile] = useState<File | null>(null);
  const [editLogoPreview, setEditLogoPreview] = useState("");
  const [editLogoRemoved, setEditLogoRemoved] = useState(false);

  // Revoke object URLs on cleanup
  useEffect(() => {
    return () => { if (logoFilePreview) URL.revokeObjectURL(logoFilePreview); };
  }, [logoFilePreview]);

  useEffect(() => {
    return () => { if (editLogoPreview && editLogoPreview.startsWith("blob:")) URL.revokeObjectURL(editLogoPreview); };
  }, [editLogoPreview]);

  const channels = data?.items || [];
  const pendingCount = Object.keys(pendingChanges).length;

  // Track inline change
  const trackChange = useCallback((channelId: number, field: string, value: string) => {
    setPendingChanges((prev) => {
      const existing = prev[channelId] || { id: channelId };
      if (field === "channel_number") {
        return { ...prev, [channelId]: { ...existing, [field]: value ? parseInt(value) : null } };
      }
      return { ...prev, [channelId]: { ...existing, [field]: value } };
    });
  }, []);

  // Apply all pending changes
  async function handleApplyAll() {
    const items: ChannelBulkUpdateItem[] = Object.values(pendingChanges);
    try {
      await bulkUpdate.mutateAsync(items);
      setPendingChanges({});
      showToast(`${items.length} channels updated`, "success");
    } catch {
      showToast("Failed to save changes", "error");
    }
  }

  // Apply single row
  async function handleApplyRow(channelId: number) {
    const change = pendingChanges[channelId];
    if (!change) return;
    try {
      await bulkUpdate.mutateAsync([change]);
      setPendingChanges((prev) => {
        const next = { ...prev };
        delete next[channelId];
        return next;
      });
      showToast("Channel updated", "success");
    } catch {
      showToast("Failed to save changes", "error");
    }
  }

  // Inline group change
  async function handleGroupChange(channelId: number, groupIds: number[]) {
    try {
      await updateGroups.mutateAsync({ id: channelId, groupIds });
      showToast("Groups updated", "success");
    } catch {
      showToast("Failed to update groups", "error");
    }
  }

  // Inline package change
  async function handlePackageChange(channelId: number, packageIds: number[]) {
    try {
      await updatePackages.mutateAsync({ id: channelId, packageIds });
      showToast("Packages updated", "success");
    } catch {
      showToast("Failed to update packages", "error");
    }
  }

  // Sync
  async function handleSync() {
    try {
      const result = await syncMut.mutateAsync();
      showToast(`Sync complete: ${result.new} new, ${result.updated} updated, ${result.orphaned} orphaned`, "success");
      setPage(1);
    } catch {
      showToast("Failed to sync channels", "error");
    }
  }

  // Delete channel
  async function handleDelete() {
    if (!deleteTarget) return;
    const isOrphaned = deleteTarget.sync_status === "orphaned";
    try {
      await deleteChannelMut.mutateAsync({ id: deleteTarget.id, force: !isOrphaned });
      showToast("Channel deleted", "success");
      setDeleteTarget(null);
    } catch {
      showToast("Failed to delete channel", "error");
    }
  }

  function getDeleteDetails(): string {
    if (!cascadeInfo) return "";
    const details: string[] = [];
    if (cascadeInfo.packages > 0) details.push(`${cascadeInfo.packages} packages`);
    if (cascadeInfo.users > 0) details.push(`${cascadeInfo.users} users`);
    let msg = details.length > 0
      ? `This will remove it from: ${details.join(", ")}.`
      : "This channel is not assigned to any packages or users.";
    if (deleteTarget && deleteTarget.sync_status !== "orphaned") {
      msg += " Warning: This channel is still synced with Flussonic and will reappear on next sync.";
    }
    return msg;
  }

  // Logo modal
  function openLogoModal(channel: ChannelResponse) {
    setLogoChannel(channel);
    setLogoFile(null);
    setLogoFilePreview("");
    setLogoUrl(channel.tvg_logo || "");
    setLogoRemovalMode(null);
  }

  async function handleLogoApply() {
    if (!logoChannel) return;
    try {
      if (logoRemovalMode) {
        await removeLogoMut.mutateAsync({ id: logoChannel.id, deleteFile: logoRemovalMode === "delete" });
        showToast("Logo removed", "success");
      } else if (logoFile) {
        await uploadLogoMut.mutateAsync({ id: logoChannel.id, file: logoFile });
        showToast("Logo uploaded", "success");
      } else if (logoUrl && logoUrl !== (logoChannel.tvg_logo || "")) {
        await uploadLogoUrlMut.mutateAsync({ id: logoChannel.id, url: logoUrl });
        showToast("Logo updated", "success");
      }
      // Remove any pending tvg_logo changes for this channel
      setPendingChanges((prev) => {
        const next = { ...prev };
        if (next[logoChannel.id]) {
          delete next[logoChannel.id].tvg_logo;
          if (Object.keys(next[logoChannel.id]).length <= 1) delete next[logoChannel.id];
        }
        return next;
      });
      setLogoChannel(null);
    } catch {
      showToast("Failed to update logo", "error");
    }
  }

  // Edit modal
  function openEditModal(channel: ChannelResponse) {
    setEditChannel(channel);
    setEditNumber(channel.channel_number?.toString() || "");
    setEditTvgId(channel.tvg_id || "");
    setEditGroupIds(channel.groups.map((g) => g.id));
    setEditLogoFile(null);
    setEditLogoPreview(channel.tvg_logo || "");
    setEditLogoRemoved(false);
  }

  async function handleEditSave() {
    if (!editChannel) return;
    try {
      // Upload logo file if selected
      let logoValue = editLogoRemoved ? "" : editLogoPreview;
      if (editLogoFile) {
        const result = await uploadLogoMut.mutateAsync({ id: editChannel.id, file: editLogoFile });
        logoValue = result.url;
      }

      // Bulk update channel fields
      await bulkUpdate.mutateAsync([{
        id: editChannel.id,
        tvg_id: editTvgId,
        tvg_logo: logoValue,
        channel_number: editNumber ? parseInt(editNumber) : null,
      }]);

      // Update groups
      await updateGroups.mutateAsync({ id: editChannel.id, groupIds: editGroupIds });

      showToast("Channel updated", "success");
      setEditChannel(null);
    } catch {
      showToast("Failed to update channel", "error");
    }
  }

  // Group/Package options for react-select
  const groupOptions = useMemo(
    () => (groups || []).map((g) => ({ value: g.id, label: g.name })),
    [groups]
  );
  const packageOptions = useMemo(
    () => (packages || []).map((p) => ({ value: p.id, label: p.name })),
    [packages]
  );

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
        <h1 className="text-2xl font-bold text-gray-800">Channels</h1>
        <div className="flex space-x-2">
          {pendingCount > 0 && (
            <Button
              onClick={handleApplyAll}
              loading={bulkUpdate.isPending}
              className="bg-green-600 hover:bg-green-700 focus:ring-green-500"
            >
              Apply All ({pendingCount})
            </Button>
          )}
          <Button onClick={handleSync} loading={syncMut.isPending}>
            Sync from Flussonic
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Group</label>
            <select
              value={groupFilter}
              onChange={(e) => { setGroupFilter(e.target.value); setPage(1); }}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">All Groups</option>
              {(groups || []).map((g) => (
                <option key={g.id} value={g.id}>{g.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">All Status</option>
              <option value="synced">Synced</option>
              <option value="orphaned">Orphaned</option>
            </select>
          </div>
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700">Search</label>
            <input
              type="text"
              value={searchInput}
              onChange={(e) => { setSearchInput(e.target.value); setPage(1); }}
              placeholder="Search channels..."
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 resizable-table" style={{ width: "100%" }}>
          <thead className="bg-gray-50">
            <tr>
              <ResizableHeader colKey="number" width={widths.number} onResize={onResize} className="w-16">
                <SortableHeader label="#" field="channel_number" sortBy={sortBy} sortDir={sortDir} onSort={toggleSort} />
              </ResizableHeader>
              <ResizableHeader colKey="logo" width={widths.logo} onResize={onResize} className="w-14">
                Logo
              </ResizableHeader>
              <ResizableHeader colKey="name" width={widths.name} onResize={onResize}>
                <SortableHeader label="Name" field="display_name" sortBy={sortBy} sortDir={sortDir} onSort={toggleSort} />
              </ResizableHeader>
              <ResizableHeader colKey="tvg-id" width={widths["tvg-id"]} onResize={onResize} className="w-28">
                <SortableHeader label="TVG ID" field="tvg_id" sortBy={sortBy} sortDir={sortDir} onSort={toggleSort} />
              </ResizableHeader>
              <ResizableHeader colKey="group" width={widths.group} onResize={onResize} className="w-32">
                Groups
              </ResizableHeader>
              <ResizableHeader colKey="archive" width={widths.archive} onResize={onResize} className="w-16">
                <SortableHeader label="Archive" field="catchup_days" sortBy={sortBy} sortDir={sortDir} onSort={toggleSort} />
              </ResizableHeader>
              <ResizableHeader colKey="packages" width={widths.packages} onResize={onResize} className="w-40">
                Packages
              </ResizableHeader>
              <ResizableHeader colKey="status" width={widths.status} onResize={onResize} className="w-20">
                <SortableHeader label="Status" field="sync_status" sortBy={sortBy} sortDir={sortDir} onSort={toggleSort} />
              </ResizableHeader>
              <ResizableHeader colKey="actions" width={widths.actions} onResize={onResize} className="w-24">
                Actions
              </ResizableHeader>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {channels.length === 0 ? (
              <EmptyState message="No channels found" colSpan={9} />
            ) : (
              channels.map((ch) => {
                const pending = pendingChanges[ch.id];
                const currentNumber = pending?.channel_number !== undefined ? (pending.channel_number ?? "") : (ch.channel_number ?? "");
                const currentTvgId = pending?.tvg_id !== undefined ? pending.tvg_id : (ch.tvg_id || "");
                const currentLogo = pending?.tvg_logo !== undefined ? pending.tvg_logo : (ch.tvg_logo || "");
                const hasChanges = !!pending;
                const isOrphaned = ch.sync_status === "orphaned";
                const catchupDisplay = ch.catchup_days == null ? "-" : String(ch.catchup_days);

                return (
                  <tr key={ch.id} className={`${isOrphaned ? "bg-gray-50 text-gray-500" : ""} ${hasChanges ? "bg-yellow-50" : ""}`}>
                    <td className="px-2 py-2">
                      <input
                        type="number"
                        min={0}
                        max={9999}
                        value={currentNumber}
                        onChange={(e) => trackChange(ch.id, "channel_number", e.target.value)}
                        className="w-14 px-1 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      />
                    </td>
                    <td className="px-2 py-2">
                      {currentLogo ? (
                        <img
                          src={currentLogo}
                          className="w-8 h-8 object-contain cursor-pointer"
                          onClick={() => openLogoModal(ch)}
                          title="Click to change"
                        />
                      ) : (
                        <button
                          onClick={() => openLogoModal(ch)}
                          className="w-8 h-8 border border-dashed border-gray-300 rounded flex items-center justify-center text-gray-400 hover:border-blue-500 hover:text-blue-500 text-xs"
                          title="Add logo"
                        >
                          +
                        </button>
                      )}
                    </td>
                    <td className="px-2 py-2">
                      <div className="font-medium text-sm">{ch.display_name || ch.stream_name}</div>
                      <div className="text-xs text-gray-500">{ch.stream_name}</div>
                    </td>
                    <td className="px-2 py-2">
                      <input
                        type="text"
                        value={currentTvgId}
                        onChange={(e) => trackChange(ch.id, "tvg_id", e.target.value)}
                        placeholder="-"
                        className="w-24 px-1 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      />
                    </td>
                    <td className="px-2 py-2">
                      <ReactSelect
                        isMulti
                        options={groupOptions}
                        value={groupOptions.filter((o) => ch.groups.some((g) => g.id === o.value))}
                        onChange={(selected: MultiValue<{ value: number; label: string }>) => {
                          handleGroupChange(ch.id, selected.map((s) => s.value));
                        }}
                        menuPortalTarget={document.body}
                        styles={{ menuPortal: (base) => ({ ...base, zIndex: 50 }), control: (base) => ({ ...base, minHeight: "30px", fontSize: "12px" }), multiValue: (base) => ({ ...base, fontSize: "11px" }) }}
                        classNamePrefix="react-select"
                      />
                    </td>
                    <td className="px-2 py-2">
                      <span className={`text-sm ${catchupDisplay === "-" ? "text-gray-400" : "text-gray-700"}`}>{catchupDisplay}</span>
                    </td>
                    <td className="px-2 py-2">
                      <ReactSelect
                        isMulti
                        options={packageOptions}
                        value={packageOptions.filter((o) => ch.packages.some((p) => p.id === o.value))}
                        onChange={(selected: MultiValue<{ value: number; label: string }>) => {
                          handlePackageChange(ch.id, selected.map((s) => s.value));
                        }}
                        menuPortalTarget={document.body}
                        styles={{ menuPortal: (base) => ({ ...base, zIndex: 50 }), control: (base) => ({ ...base, minHeight: "30px", fontSize: "12px" }), multiValue: (base) => ({ ...base, fontSize: "11px" }) }}
                        classNamePrefix="react-select"
                      />
                    </td>
                    <td className="px-2 py-2">
                      <Badge variant={ch.sync_status === "synced" ? "green" : "yellow"}>
                        {ch.sync_status === "synced" ? "sync" : "orph"}
                      </Badge>
                    </td>
                    <td className="px-2 py-2">
                      <div className="flex items-center space-x-1">
                        <Button
                          size="sm"
                          variant={hasChanges ? "primary" : "ghost"}
                          disabled={!hasChanges}
                          onClick={() => handleApplyRow(ch.id)}
                          className={hasChanges ? "bg-green-600 hover:bg-green-700" : ""}
                        >
                          Apply
                        </Button>
                        <Button size="sm" onClick={() => openEditModal(ch)}>Edit</Button>
                        <Button size="sm" variant="danger" onClick={() => setDeleteTarget(ch)}>Del</Button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>

        <Pagination
          page={data?.page || 1}
          pages={data?.pages || 0}
          total={data?.total || 0}
          onPageChange={setPage}
          perPage={perPage}
          onPerPageChange={(pp) => { setPerPage(pp); setPage(1); }}
          label="channels"
        />
      </div>

      {/* Delete Confirmation */}
      {!!deleteTarget && (
        <ConfirmDialog
          open={!!deleteTarget}
          onClose={() => setDeleteTarget(null)}
          onConfirm={handleDelete}
          title="Delete Channel"
          message={`Are you sure you want to delete "${deleteTarget?.display_name || deleteTarget?.stream_name}"?`}
          details={getDeleteDetails()}
          loading={deleteChannelMut.isPending}
        />
      )}

      {/* Logo Modal */}
      {!!logoChannel && (
        <Modal
          open={!!logoChannel}
          onClose={() => setLogoChannel(null)}
          title="Edit Logo"
          footer={
            <>
              <Button variant="secondary" onClick={() => setLogoChannel(null)}>Cancel</Button>
              <Button onClick={handleLogoApply} loading={uploadLogoMut.isPending || uploadLogoUrlMut.isPending || removeLogoMut.isPending}>Apply</Button>
            </>
          }
        >
          <div className="space-y-4">
            <div className="flex items-center justify-center">
              {logoRemovalMode || (!logoFile && !logoUrl) ? (
                <div className="w-32 h-32 border-2 border-dashed border-gray-300 rounded flex items-center justify-center text-gray-400">No logo</div>
              ) : (
                <img
                  src={logoFilePreview || logoUrl}
                  className="w-32 h-32 object-contain border rounded"
                />
              )}
            </div>
            <div className="flex justify-center space-x-2">
              <input ref={logoFileRef} type="file" accept="image/*" className="hidden" onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) { setLogoFile(f); setLogoFilePreview(URL.createObjectURL(f)); setLogoRemovalMode(null); setLogoUrl(""); }
              }} />
              <button type="button" onClick={() => logoFileRef.current?.click()} className="px-4 py-2 border border-gray-300 rounded-md text-sm text-gray-700 hover:bg-gray-50">Choose File</button>
              <button type="button" onClick={() => { setLogoRemovalMode("db"); setLogoFile(null); setLogoFilePreview(""); setLogoUrl(""); }} className="px-4 py-2 border border-red-300 rounded-md text-sm text-red-700 hover:bg-red-50">Remove URL</button>
              <button type="button" onClick={() => { setLogoRemovalMode("delete"); setLogoFile(null); setLogoFilePreview(""); setLogoUrl(""); }} className="px-4 py-2 bg-red-600 text-white rounded-md text-sm hover:bg-red-700">Remove + Delete File</button>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500">Or paste logo URL</label>
              <input
                type="text"
                value={logoUrl}
                onChange={(e) => { setLogoUrl(e.target.value); setLogoFile(null); setLogoFilePreview(""); setLogoRemovalMode(null); }}
                placeholder="https://example.com/logo.png"
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
        </Modal>
      )}

      {/* Edit Channel Modal */}
      {!!editChannel && (
        <Modal
          open={!!editChannel}
          onClose={() => setEditChannel(null)}
          title={`Edit: ${editChannel?.display_name || editChannel?.stream_name || ""}`}
          footer={
            <>
              <Button variant="secondary" onClick={() => setEditChannel(null)}>Cancel</Button>
              <Button onClick={handleEditSave}>Save</Button>
            </>
          }
        >
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Stream Name</label>
              <input type="text" readOnly value={editChannel.stream_name} className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-gray-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Display Name</label>
              <input type="text" readOnly value={editChannel.display_name || ""} className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-gray-500" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Channel #</label>
                <input type="number" min={0} max={9999} value={editNumber} onChange={(e) => setEditNumber(e.target.value)} className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Archive Days</label>
                <div className="mt-1 px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-gray-500 text-sm">
                  {editChannel.catchup_days == null ? "-" : String(editChannel.catchup_days)}
                </div>
                <p className="mt-1 text-xs text-gray-400">Imported from Flussonic.</p>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">TVG ID (EPG ID)</label>
              <input type="text" value={editTvgId} onChange={(e) => setEditTvgId(e.target.value)} className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Logo</label>
              <div className="mt-1 flex items-center space-x-4">
                {!editLogoRemoved && editLogoPreview && (
                  <img src={editLogoPreview} className="w-16 h-16 object-contain border rounded" />
                )}
                <input ref={editLogoFileRef} type="file" accept="image/*" className="hidden" onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) { setEditLogoFile(f); setEditLogoPreview(URL.createObjectURL(f)); setEditLogoRemoved(false); }
                }} />
                <button type="button" onClick={() => editLogoFileRef.current?.click()} className="px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-700 hover:bg-gray-50">Choose File</button>
                <button type="button" onClick={() => { setEditLogoRemoved(true); setEditLogoFile(null); setEditLogoPreview(""); }} className="px-3 py-2 border border-red-300 rounded-md text-sm text-red-700 hover:bg-red-50">Remove</button>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Groups</label>
              <ReactSelect
                isMulti
                options={groupOptions}
                value={groupOptions.filter((o) => editGroupIds.includes(o.value))}
                onChange={(selected: MultiValue<{ value: number; label: string }>) => setEditGroupIds(selected.map((s) => s.value))}
                menuPortalTarget={document.body}
                styles={{ menuPortal: (base) => ({ ...base, zIndex: 50 }) }}
                className="mt-1"
                classNamePrefix="react-select"
              />
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
