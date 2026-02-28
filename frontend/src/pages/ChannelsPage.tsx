import { useState, useMemo, useCallback, useRef, useEffect } from "react";
import type { MultiValue } from "react-select";
import ReactSelect from "react-select";
import { useSearchParams } from "react-router-dom";
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
import { Card } from "../components/ui/Card";
import { FilterBar } from "../components/ui/FilterBar";
import { Input } from "../components/ui/Input";
import { PageHeader } from "../components/ui/PageHeader";
import { Select } from "../components/ui/Select";
import { fieldLabelClass } from "../components/ui/fieldStyles";
import { SortableHeader } from "../components/table/SortableHeader";
import { ResizableHeader } from "../components/table/ResizableHeader";
import type { ChannelResponse, ChannelBulkUpdateItem } from "../api/types";

interface PendingChange {
  id: number;
  tvg_id?: string;
  tvg_logo?: string;
  channel_number?: number | null;
}

function parsePositiveInt(value: string | null, fallback: number) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

const compactCellInputClass =
  "h-8 rounded-md border border-slate-300 px-1.5 py-1 text-sm text-slate-900 outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100";

const compactMultiSelectStyles = {
  menuPortal: (base: object) => ({ ...base, zIndex: 50 }),
  control: (base: object) => ({
    ...base,
    minHeight: "30px",
    fontSize: "12px",
    borderColor: "#cbd5e1",
    boxShadow: "none",
  }),
  multiValue: (base: object) => ({ ...base, fontSize: "11px" }),
};

const portalOnlySelectStyles = {
  menuPortal: (base: object) => ({ ...base, zIndex: 50 }),
};

export function ChannelsPage() {
  const { showToast } = useToast();
  const { sortBy, sortDir, toggleSort } = useSortable("channel_number");
  const { widths, onResize } = useColumnResize("channelsTableWidths");
  const [searchParams, setSearchParams] = useSearchParams();

  const page = parsePositiveInt(searchParams.get("page"), 1);
  const perPage = parsePositiveInt(searchParams.get("perPage"), 20);
  const groupFilter = searchParams.get("group") ?? "";
  const statusFilter = searchParams.get("status") ?? "";
  const urlSearch = searchParams.get("search") ?? "";

  const [searchInput, setSearchInput] = useState(urlSearch);
  const search = useDebounce(searchInput);

  useEffect(() => {
    setSearchInput(urlSearch);
  }, [urlSearch]);

  function updateParams(patch: Record<string, string | undefined>) {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(patch)) {
      if (!value) next.delete(key);
      else next.set(key, value);
    }
    setSearchParams(next);
  }

  useEffect(() => {
    const trimmed = search.trim();
    if (trimmed === urlSearch) return;
    const next = new URLSearchParams(searchParams);
    if (trimmed) next.set("search", trimmed);
    else next.delete("search");
    next.set("page", "1");
    setSearchParams(next);
  }, [search, searchParams, setSearchParams, urlSearch]);

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
      updateParams({ page: "1" });
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
      <PageHeader
        title="Channels"
        description="Manage channel metadata, logos, groups, and package assignments."
        actions={
          <div className="flex flex-wrap gap-2">
          {pendingCount > 0 && (
            <Button
              onClick={handleApplyAll}
              loading={bulkUpdate.isPending}
              className="border-emerald-600 bg-emerald-600 hover:bg-emerald-700"
            >
              Apply All ({pendingCount})
            </Button>
          )}
          <Button onClick={handleSync} loading={syncMut.isPending}>
            Sync from Flussonic
          </Button>
          </div>
        }
      />

      <FilterBar>
        <Select
          label="Group"
          value={groupFilter}
          onChange={(e) => updateParams({ group: e.target.value || undefined, page: "1" })}
        >
          <option value="">All Groups</option>
          {(groups || []).map((g) => (
            <option key={g.id} value={g.id}>{g.name}</option>
          ))}
        </Select>
        <Select
          label="Status"
          value={statusFilter}
          onChange={(e) => updateParams({ status: e.target.value || undefined, page: "1" })}
        >
          <option value="">All Status</option>
          <option value="synced">Synced</option>
          <option value="orphaned">Orphaned</option>
        </Select>
        <div className="md:col-span-2">
          <Input
            label="Search"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search channels..."
          />
        </div>
      </FilterBar>

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 resizable-table" style={{ width: "100%" }}>
            <thead className="bg-slate-50">
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
              <ResizableHeader colKey="actions" width={widths.actions} onResize={onResize} className="w-40" minWidth={160}>
                Actions
              </ResizableHeader>
            </tr>
          </thead>
            <tbody className="bg-white divide-y divide-slate-200">
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
                  <tr key={ch.id} className={`${isOrphaned ? "bg-slate-50 text-slate-500" : ""} ${hasChanges ? "bg-amber-50" : ""}`}>
                    <td className="px-2 py-2">
                      <input
                        type="number"
                        min={0}
                        max={9999}
                        value={currentNumber}
                        onChange={(e) => trackChange(ch.id, "channel_number", e.target.value)}
                        className={`${compactCellInputClass} w-14`}
                        aria-label={`Channel number for ${ch.display_name || ch.stream_name}`}
                      />
                    </td>
                    <td className="px-2 py-2">
                      {currentLogo ? (
                        <button
                          type="button"
                          onClick={() => openLogoModal(ch)}
                          className="flex h-8 w-8 items-center justify-center rounded border border-transparent hover:border-sky-200 hover:bg-sky-50"
                          title="Edit logo"
                          aria-label={`Edit logo for ${ch.display_name || ch.stream_name}`}
                        >
                          <img
                            src={currentLogo}
                            className="h-8 w-8 object-contain"
                            alt=""
                          />
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={() => openLogoModal(ch)}
                          className="flex h-8 w-8 items-center justify-center rounded border border-dashed border-slate-300 text-xs text-slate-400 hover:border-sky-500 hover:text-sky-500"
                          title="Add logo"
                          aria-label={`Add logo for ${ch.display_name || ch.stream_name}`}
                        >
                          +
                        </button>
                      )}
                    </td>
                    <td className="px-2 py-2">
                      <div className="font-medium text-sm">{ch.display_name || ch.stream_name}</div>
                      <div className="text-xs text-slate-500">{ch.stream_name}</div>
                    </td>
                    <td className="px-2 py-2">
                      <input
                        type="text"
                        value={currentTvgId}
                        onChange={(e) => trackChange(ch.id, "tvg_id", e.target.value)}
                        placeholder="-"
                        className={`${compactCellInputClass} w-24`}
                        aria-label={`TVG ID for ${ch.display_name || ch.stream_name}`}
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
                        styles={compactMultiSelectStyles}
                        classNamePrefix="react-select"
                      />
                    </td>
                    <td className="px-2 py-2">
                      <span className={`text-sm ${catchupDisplay === "-" ? "text-slate-400" : "text-slate-700"}`}>{catchupDisplay}</span>
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
                        styles={compactMultiSelectStyles}
                        classNamePrefix="react-select"
                      />
                    </td>
                    <td className="px-2 py-2">
                      <Badge variant={ch.sync_status === "synced" ? "green" : "yellow"}>
                        {ch.sync_status === "synced" ? "sync" : "orph"}
                      </Badge>
                    </td>
                    <td className="px-2 py-2">
                      <div className="flex items-center gap-1">
                        <Button
                          size="sm"
                          variant={hasChanges ? "primary" : "ghost"}
                          disabled={!hasChanges}
                          onClick={() => handleApplyRow(ch.id)}
                          className={hasChanges ? "border-emerald-600 bg-emerald-600 hover:bg-emerald-700" : ""}
                        >
                          Apply
                        </Button>
                        <Button size="sm" variant="secondary" onClick={() => openEditModal(ch)}>Edit</Button>
                        <Button size="sm" variant="danger" onClick={() => setDeleteTarget(ch)}>Del</Button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
          </table>
        </div>

        <Pagination
          page={data?.page || 1}
          pages={data?.pages || 0}
          total={data?.total || 0}
          onPageChange={(nextPage) => updateParams({ page: String(nextPage) })}
          perPage={perPage}
          onPerPageChange={(pp) => { updateParams({ perPage: String(pp), page: "1" }); }}
          label="channels"
        />
      </Card>

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
                <div className="flex h-32 w-32 items-center justify-center rounded-lg border-2 border-dashed border-slate-300 text-slate-400">No logo</div>
              ) : (
                <img
                  src={logoFilePreview || logoUrl}
                  className="h-32 w-32 rounded-lg border border-slate-200 object-contain"
                  alt="Channel logo preview"
                />
              )}
            </div>
            <div className="flex flex-wrap justify-center gap-2">
              <input ref={logoFileRef} type="file" accept="image/*" className="hidden" onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) { setLogoFile(f); setLogoFilePreview(URL.createObjectURL(f)); setLogoRemovalMode(null); setLogoUrl(""); }
              }} />
              <Button type="button" variant="secondary" onClick={() => logoFileRef.current?.click()}>
                Choose File
              </Button>
              <Button
                type="button"
                variant="secondary"
                className="border-rose-300 text-rose-700 hover:bg-rose-50"
                onClick={() => { setLogoRemovalMode("db"); setLogoFile(null); setLogoFilePreview(""); setLogoUrl(""); }}
              >
                Remove URL
              </Button>
              <Button
                type="button"
                variant="danger"
                onClick={() => { setLogoRemovalMode("delete"); setLogoFile(null); setLogoFilePreview(""); setLogoUrl(""); }}
              >
                Remove + Delete File
              </Button>
            </div>
            <Input
              label="Or paste logo URL"
              type="text"
              value={logoUrl}
              onChange={(e) => { setLogoUrl(e.target.value); setLogoFile(null); setLogoFilePreview(""); setLogoRemovalMode(null); }}
              placeholder="https://example.com/logo.png"
            />
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
            <Input label="Stream Name" type="text" readOnly value={editChannel.stream_name} className="bg-slate-50 text-slate-500" />
            <Input label="Display Name" type="text" readOnly value={editChannel.display_name || ""} className="bg-slate-50 text-slate-500" />
            <div className="grid grid-cols-2 gap-4">
              <Input
                label="Channel #"
                type="number"
                min={0}
                max={9999}
                value={editNumber}
                onChange={(e) => setEditNumber(e.target.value)}
              />
              <div>
                <label className={fieldLabelClass}>Archive Days</label>
                <div className="mt-1 rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-500">
                  {editChannel.catchup_days == null ? "-" : String(editChannel.catchup_days)}
                </div>
                <p className="mt-1 text-xs text-slate-400">Imported from Flussonic.</p>
              </div>
            </div>
            <Input label="TVG ID (EPG ID)" type="text" value={editTvgId} onChange={(e) => setEditTvgId(e.target.value)} />
            <div>
              <label className={fieldLabelClass}>Logo</label>
              <div className="mt-1 flex flex-wrap items-center gap-4">
                {!editLogoRemoved && editLogoPreview && (
                  <img src={editLogoPreview} className="h-16 w-16 rounded border border-slate-200 object-contain" alt="Edit logo preview" />
                )}
                <input ref={editLogoFileRef} type="file" accept="image/*" className="hidden" onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) { setEditLogoFile(f); setEditLogoPreview(URL.createObjectURL(f)); setEditLogoRemoved(false); }
                }} />
                <Button type="button" variant="secondary" onClick={() => editLogoFileRef.current?.click()}>
                  Choose File
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  className="border-rose-300 text-rose-700 hover:bg-rose-50"
                  onClick={() => { setEditLogoRemoved(true); setEditLogoFile(null); setEditLogoPreview(""); }}
                >
                  Remove
                </Button>
              </div>
            </div>
            <div>
              <label className={fieldLabelClass}>Groups</label>
              <ReactSelect
                isMulti
                options={groupOptions}
                value={groupOptions.filter((o) => editGroupIds.includes(o.value))}
                onChange={(selected: MultiValue<{ value: number; label: string }>) => setEditGroupIds(selected.map((s) => s.value))}
                menuPortalTarget={document.body}
                styles={portalOnlySelectStyles}
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
