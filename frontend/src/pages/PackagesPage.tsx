import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Pencil, Trash2 } from "lucide-react";
import {
  usePackages,
  useCreatePackage,
  useUpdatePackage,
  useDeletePackage,
  usePackageDetail,
  useRemoveChannelFromPackage,
} from "../hooks/usePackages";
import {
  useTariffs,
  useCreateTariff,
  useUpdateTariff,
  useDeleteTariff,
} from "../hooks/useTariffs";
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
import { fieldControlClass, fieldLabelClass } from "../components/ui/fieldStyles";
import { SortableHeader } from "../components/table/SortableHeader";
import { ResizableHeader } from "../components/table/ResizableHeader";
import type { PackageWithCount, TariffWithCount } from "../api/types";
import { formatChannelPrimary, formatChannelSecondary } from "../utils/channels";

const defaultPerPage = 20;

function parsePositiveInt(value: string | null, fallback: number) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

export function PackagesPage() {
  const { data: packages, isLoading: packagesLoading } = usePackages();
  const { data: tariffs, isLoading: tariffsLoading } = useTariffs();
  const { showToast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();

  const pkgPage = parsePositiveInt(searchParams.get("pkgPage"), 1);
  const pkgPerPage = parsePositiveInt(searchParams.get("pkgPerPage"), defaultPerPage);
  const tariffPage = parsePositiveInt(searchParams.get("tariffPage"), 1);
  const tariffPerPage = parsePositiveInt(searchParams.get("tariffPerPage"), defaultPerPage);

  // Package sort
  const pkgSort = useSortable("name");
  const pkgResize = useColumnResize("packagesTableWidths");

  // Tariff sort
  const tariffSort = useSortable("name");
  const tariffResize = useColumnResize("tariffsTableWidths");

  // Package modals
  const [pkgModalOpen, setPkgModalOpen] = useState(false);
  const [editingPkg, setEditingPkg] = useState<PackageWithCount | null>(null);
  const [pkgName, setPkgName] = useState("");
  const [pkgDescription, setPkgDescription] = useState("");
  const [deletePkgTarget, setDeletePkgTarget] = useState<PackageWithCount | null>(null);

  // Package detail (for editing with channels list)
  const [detailPkgId, setDetailPkgId] = useState<number | undefined>(undefined);
  const { data: pkgDetail } = usePackageDetail(detailPkgId);
  const removeChannelMut = useRemoveChannelFromPackage();

  // Tariff modals
  const [tariffModalOpen, setTariffModalOpen] = useState(false);
  const [editingTariff, setEditingTariff] = useState<TariffWithCount | null>(null);
  const [tariffName, setTariffName] = useState("");
  const [tariffDescription, setTariffDescription] = useState("");
  const [selectedPkgIds, setSelectedPkgIds] = useState<number[]>([]);
  const [deleteTariffTarget, setDeleteTariffTarget] = useState<TariffWithCount | null>(null);

  // Mutations
  const createPkg = useCreatePackage();
  const updatePkg = useUpdatePackage();
  const deletePkgMut = useDeletePackage();
  const createTariffMut = useCreateTariff();
  const updateTariffMut = useUpdateTariff();
  const deleteTariffMut = useDeleteTariff();

  // Sorted packages
  const sortedPackages = useMemo(() => {
    if (!packages) return [];
    return [...packages].sort((a, b) => {
      const dir = pkgSort.sortDir === "asc" ? 1 : -1;
      if (pkgSort.sortBy === "name") return dir * a.name.localeCompare(b.name);
      if (pkgSort.sortBy === "description") return dir * (a.description || "").localeCompare(b.description || "");
      if (pkgSort.sortBy === "channel_count") return dir * (a.channel_count - b.channel_count);
      return 0;
    });
  }, [packages, pkgSort.sortBy, pkgSort.sortDir]);

  const pkgTotalPages = Math.max(1, Math.ceil(sortedPackages.length / pkgPerPage));
  const pkgCurrentPage = Math.min(pkgPage, pkgTotalPages);
  const pagedPackages = useMemo(
    () => sortedPackages.slice((pkgCurrentPage - 1) * pkgPerPage, pkgCurrentPage * pkgPerPage),
    [pkgCurrentPage, pkgPerPage, sortedPackages],
  );

  // Sorted tariffs
  const sortedTariffs = useMemo(() => {
    if (!tariffs) return [];
    return [...tariffs].sort((a, b) => {
      const dir = tariffSort.sortDir === "asc" ? 1 : -1;
      if (tariffSort.sortBy === "name") return dir * a.name.localeCompare(b.name);
      if (tariffSort.sortBy === "description") return dir * (a.description || "").localeCompare(b.description || "");
      if (tariffSort.sortBy === "channel_count") return dir * (a.channel_count - b.channel_count);
      return 0;
    });
  }, [tariffs, tariffSort.sortBy, tariffSort.sortDir]);

  const tariffTotalPages = Math.max(1, Math.ceil(sortedTariffs.length / tariffPerPage));
  const tariffCurrentPage = Math.min(tariffPage, tariffTotalPages);
  const pagedTariffs = useMemo(
    () => sortedTariffs.slice((tariffCurrentPage - 1) * tariffPerPage, tariffCurrentPage * tariffPerPage),
    [tariffCurrentPage, tariffPerPage, sortedTariffs],
  );

  function updateParams(patch: Record<string, string | undefined>) {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(patch)) {
      if (!value) next.delete(key);
      else next.set(key, value);
    }
    setSearchParams(next);
  }

  // Package handlers
  function openAddPkg() {
    setEditingPkg(null);
    setDetailPkgId(undefined);
    setPkgName("");
    setPkgDescription("");
    setPkgModalOpen(true);
  }

  function openEditPkg(pkg: PackageWithCount) {
    setEditingPkg(pkg);
    setDetailPkgId(pkg.id);
    setPkgName(pkg.name);
    setPkgDescription(pkg.description || "");
    setPkgModalOpen(true);
  }

  async function handleSavePkg() {
    const name = pkgName.trim();
    if (!name) {
      showToast("Please enter a package name", "error");
      return;
    }
    try {
      const description = pkgDescription.trim() || null;
      if (editingPkg) {
        await updatePkg.mutateAsync({
          id: editingPkg.id,
          data: { name, description },
        });
        showToast("Package updated", "success");
      } else {
        await createPkg.mutateAsync({ name, description });
        showToast("Package created", "success");
      }
      setPkgModalOpen(false);
    } catch {
      showToast("Failed to save package", "error");
    }
  }

  async function handleDeletePkg() {
    if (!deletePkgTarget) return;
    try {
      await deletePkgMut.mutateAsync(deletePkgTarget.id);
      showToast("Package deleted", "success");
      setDeletePkgTarget(null);
    } catch {
      showToast("Failed to delete package", "error");
    }
  }

  async function handleRemoveChannel(channelId: number) {
    if (!detailPkgId) return;
    try {
      await removeChannelMut.mutateAsync({ packageId: detailPkgId, channelId });
      showToast("Channel removed from package", "success");
    } catch {
      showToast("Failed to remove channel", "error");
    }
  }

  // Tariff handlers
  function openAddTariff() {
    setEditingTariff(null);
    setTariffName("");
    setTariffDescription("");
    setSelectedPkgIds([]);
    setTariffModalOpen(true);
  }

  function openEditTariff(tariff: TariffWithCount) {
    setEditingTariff(tariff);
    setTariffName(tariff.name);
    setTariffDescription(tariff.description || "");
    setSelectedPkgIds(tariff.packages.map((p) => p.id));
    setTariffModalOpen(true);
  }

  async function handleSaveTariff() {
    const name = tariffName.trim();
    if (!name) {
      showToast("Please enter a tariff name", "error");
      return;
    }
    try {
      const description = tariffDescription.trim() || null;
      if (editingTariff) {
        await updateTariffMut.mutateAsync({
          id: editingTariff.id,
          data: { name, description, package_ids: selectedPkgIds },
        });
        showToast("Tariff updated", "success");
      } else {
        await createTariffMut.mutateAsync({ name, description, package_ids: selectedPkgIds });
        showToast("Tariff created", "success");
      }
      setTariffModalOpen(false);
    } catch {
      showToast("Failed to save tariff", "error");
    }
  }

  async function handleDeleteTariff() {
    if (!deleteTariffTarget) return;
    try {
      await deleteTariffMut.mutateAsync(deleteTariffTarget.id);
      showToast("Tariff deleted", "success");
      setDeleteTariffTarget(null);
    } catch {
      showToast("Failed to delete tariff", "error");
    }
  }

  function togglePkgId(id: number) {
    setSelectedPkgIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  }

  if (packagesLoading || tariffsLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner />
      </div>
    );
  }

  const pkgChannels = pkgDetail?.channels || [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Packages & Tariffs"
        description="Manage channel packages and compose tariffs from those packages."
      />

      <div className="space-y-6">
        <Card>
          <div className="flex items-center justify-between border-b border-border px-6 py-4">
            <h2 className="text-lg font-semibold text-card-foreground">Packages</h2>
            <Button size="sm" onClick={openAddPkg}>+ Add</Button>
          </div>
          <div className="overflow-x-auto">
            <table className="resizable-table min-w-full divide-y divide-border" style={{ width: "100%" }}>
              <thead className="bg-muted">
                <tr>
                  <ResizableHeader colKey="name" width={pkgResize.widths.name} onResize={pkgResize.onResize}>
                    <SortableHeader label="Name" field="name" sortBy={pkgSort.sortBy} sortDir={pkgSort.sortDir} onSort={pkgSort.toggleSort} />
                  </ResizableHeader>
                  <ResizableHeader colKey="description" width={pkgResize.widths.description} onResize={pkgResize.onResize} className="hidden sm:table-cell">
                    <SortableHeader label="Description" field="description" sortBy={pkgSort.sortBy} sortDir={pkgSort.sortDir} onSort={pkgSort.toggleSort} />
                  </ResizableHeader>
                  <ResizableHeader colKey="channels" width={pkgResize.widths.channels} onResize={pkgResize.onResize} className="w-28">
                    <SortableHeader label="Channels" field="channel_count" sortBy={pkgSort.sortBy} sortDir={pkgSort.sortDir} onSort={pkgSort.toggleSort} />
                  </ResizableHeader>
                  <ResizableHeader colKey="actions" width={pkgResize.widths.actions} onResize={pkgResize.onResize} className="w-40" minWidth={160}>
                    Actions
                  </ResizableHeader>
                </tr>
              </thead>
              <tbody className="divide-y divide-border bg-card">
                {sortedPackages.length === 0 ? (
                  <EmptyState message="No packages yet" colSpan={4} />
                ) : (
                  pagedPackages.map((p) => (
                    <tr key={p.id}>
                      <td className="px-4 py-3">
                        <div className="truncate font-semibold text-foreground" title={p.name}>{p.name}</div>
                      </td>
                      <td className="hidden px-4 py-3 sm:table-cell">
                        <div className="truncate text-sm text-muted-foreground" title={p.description || undefined}>{p.description || "-"}</div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-flex min-w-8 justify-center rounded-md border border-border bg-card px-2 py-1 text-sm font-semibold text-foreground">
                          {p.channel_count}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-2">
                          <Button
                            size="sm"
                            variant="secondary"
                            className="h-8 w-8 px-0"
                            onClick={() => openEditPkg(p)}
                            aria-label={`Edit package ${p.name}`}
                            title="Edit"
                          >
                            <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
                          </Button>
                          <Button
                            size="sm"
                            variant="danger"
                            className="h-8 w-8 px-0"
                            onClick={() => setDeletePkgTarget(p)}
                            aria-label={`Delete package ${p.name}`}
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
            page={pkgCurrentPage}
            pages={pkgTotalPages}
            total={sortedPackages.length}
            onPageChange={(nextPage) => updateParams({ pkgPage: String(nextPage) })}
            perPage={pkgPerPage}
            onPerPageChange={(nextPerPage) => {
              updateParams({ pkgPerPage: String(nextPerPage), pkgPage: "1" });
            }}
            label="packages"
          />
        </Card>

        <Card>
          <div className="flex items-center justify-between border-b border-border px-6 py-4">
            <h2 className="text-lg font-semibold text-card-foreground">Tariffs</h2>
            <Button size="sm" onClick={openAddTariff}>+ Add</Button>
          </div>
          <div className="overflow-x-auto">
            <table className="resizable-table min-w-full divide-y divide-border" style={{ width: "100%" }}>
              <thead className="bg-muted">
                <tr>
                  <ResizableHeader colKey="name" width={tariffResize.widths.name} onResize={tariffResize.onResize}>
                    <SortableHeader label="Name" field="name" sortBy={tariffSort.sortBy} sortDir={tariffSort.sortDir} onSort={tariffSort.toggleSort} />
                  </ResizableHeader>
                  <ResizableHeader colKey="description" width={tariffResize.widths.description} onResize={tariffResize.onResize} className="hidden sm:table-cell">
                    <SortableHeader label="Description" field="description" sortBy={tariffSort.sortBy} sortDir={tariffSort.sortDir} onSort={tariffSort.toggleSort} />
                  </ResizableHeader>
                  <ResizableHeader colKey="channels" width={tariffResize.widths.channels} onResize={tariffResize.onResize} className="w-28">
                    <SortableHeader label="Channels" field="channel_count" sortBy={tariffSort.sortBy} sortDir={tariffSort.sortDir} onSort={tariffSort.toggleSort} />
                  </ResizableHeader>
                  <ResizableHeader colKey="actions" width={tariffResize.widths.actions} onResize={tariffResize.onResize} className="w-40" minWidth={160}>
                    Actions
                  </ResizableHeader>
                </tr>
              </thead>
              <tbody className="divide-y divide-border bg-card">
                {sortedTariffs.length === 0 ? (
                  <EmptyState message="No tariffs yet" colSpan={4} />
                ) : (
                  pagedTariffs.map((t) => (
                    <tr key={t.id}>
                      <td className="px-4 py-3">
                        <div className="truncate font-semibold text-foreground" title={t.name}>{t.name}</div>
                      </td>
                      <td className="hidden px-4 py-3 sm:table-cell">
                        <div className="truncate text-sm text-muted-foreground" title={t.description || undefined}>{t.description || "-"}</div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-flex min-w-8 justify-center rounded-md border border-border bg-card px-2 py-1 text-sm font-semibold text-foreground">
                          {t.channel_count}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-2">
                          <Button
                            size="sm"
                            variant="secondary"
                            className="h-8 w-8 px-0"
                            onClick={() => openEditTariff(t)}
                            aria-label={`Edit tariff ${t.name}`}
                            title="Edit"
                          >
                            <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
                          </Button>
                          <Button
                            size="sm"
                            variant="danger"
                            className="h-8 w-8 px-0"
                            onClick={() => setDeleteTariffTarget(t)}
                            aria-label={`Delete tariff ${t.name}`}
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
            page={tariffCurrentPage}
            pages={tariffTotalPages}
            total={sortedTariffs.length}
            onPageChange={(nextPage) => updateParams({ tariffPage: String(nextPage) })}
            perPage={tariffPerPage}
            onPerPageChange={(nextPerPage) => {
              updateParams({ tariffPerPage: String(nextPerPage), tariffPage: "1" });
            }}
            label="tariffs"
          />
        </Card>
      </div>

      {pkgModalOpen && (
        <Modal
          open={pkgModalOpen}
          onClose={() => setPkgModalOpen(false)}
          title={editingPkg ? "Edit Package" : "Add Package"}
          footer={
            <>
              <Button variant="secondary" onClick={() => setPkgModalOpen(false)}>Cancel</Button>
              <Button onClick={handleSavePkg} loading={createPkg.isPending || updatePkg.isPending}>Save</Button>
            </>
          }
      >
        <div className="space-y-4">
          <Input
            label="Name"
              type="text"
              value={pkgName}
              onChange={(e) => setPkgName(e.target.value)}
              autoFocus
          />
          <div>
            <label className={fieldLabelClass}>Description</label>
            <textarea
              value={pkgDescription}
              onChange={(e) => setPkgDescription(e.target.value)}
              rows={2}
              className={fieldControlClass}
            />
          </div>
          {editingPkg ? (
            <div>
              <label className={fieldLabelClass}>Assigned Channels</label>
              <div className="mt-2 max-h-48 overflow-y-auto divide-y divide-border rounded-md border border-border">
                {pkgChannels.length === 0 ? (
                  <div className="px-3 py-3 text-sm text-muted-foreground">No channels assigned.</div>
                ) : (
                  [...pkgChannels]
                    .sort((a, b) => {
                      const na = (a.display_name || a.stream_name || a.tvg_name || "").toLowerCase();
                      const nb = (b.display_name || b.stream_name || b.tvg_name || "").toLowerCase();
                      return na.localeCompare(nb);
                    })
                    .map((ch) => {
                      const primary = formatChannelPrimary(ch);
                      const secondary = formatChannelSecondary(ch);
                      return (
                        <div key={ch.id} className="flex items-center justify-between px-3 py-2">
                          <div>
                            <div className="text-sm text-foreground">{primary}</div>
                            {secondary && <div className="text-xs text-muted-foreground">{secondary}</div>}
                          </div>
                          <Button
                            type="button"
                            size="sm"
                            variant="danger"
                            onClick={() => handleRemoveChannel(ch.id)}
                          >
                            Remove
                          </Button>
                        </div>
                      );
                    })
                )}
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Note: Channels are assigned from the Channels page.</p>
          )}
        </div>
      </Modal>
      )}

      {!!deletePkgTarget && (
        <ConfirmDialog
        open={!!deletePkgTarget}
        onClose={() => setDeletePkgTarget(null)}
        onConfirm={handleDeletePkg}
        title="Delete Package"
        message={`Are you sure you want to delete "${deletePkgTarget?.name}"?`}
        details="This will remove the package from all tariffs and users."
        loading={deletePkgMut.isPending}
      />
      )}

      {tariffModalOpen && (
        <Modal
        open={tariffModalOpen}
        onClose={() => setTariffModalOpen(false)}
        title={editingTariff ? "Edit Tariff" : "Add Tariff"}
        footer={
          <>
            <Button variant="secondary" onClick={() => setTariffModalOpen(false)}>Cancel</Button>
            <Button onClick={handleSaveTariff} loading={createTariffMut.isPending || updateTariffMut.isPending}>Save</Button>
          </>
        }
      >
        <div className="space-y-4">
          <Input
            label="Name"
              type="text"
              value={tariffName}
              onChange={(e) => setTariffName(e.target.value)}
              autoFocus
          />
          <div>
            <label className={fieldLabelClass}>Description</label>
            <textarea
              value={tariffDescription}
              onChange={(e) => setTariffDescription(e.target.value)}
              rows={2}
              className={fieldControlClass}
            />
          </div>
          <div>
            <label className={`${fieldLabelClass} mb-2`}>Packages</label>
            <div className="max-h-48 space-y-2 overflow-y-auto rounded-md border border-border p-2">
              {(packages || []).map((p) => (
                <label key={p.id} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={selectedPkgIds.includes(p.id)}
                    onChange={() => togglePkgId(p.id)}
                    className="rounded border-input text-primary focus:ring-ring"
                  />
                  <span className="ml-2 text-sm">{p.name}</span>
                </label>
              ))}
            </div>
          </div>
        </div>
      </Modal>
      )}

      {!!deleteTariffTarget && (
        <ConfirmDialog
        open={!!deleteTariffTarget}
        onClose={() => setDeleteTariffTarget(null)}
        onConfirm={handleDeleteTariff}
        title="Delete Tariff"
        message={`Are you sure you want to delete "${deleteTariffTarget?.name}"?`}
        details="This will remove the tariff from all users."
        loading={deleteTariffMut.isPending}
      />
      )}
    </div>
  );
}
