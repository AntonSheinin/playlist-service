import { useState, useMemo } from "react";
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
import { fieldControlClass, fieldLabelClass } from "../components/ui/fieldStyles";
import { SortableHeader } from "../components/table/SortableHeader";
import { ResizableHeader } from "../components/table/ResizableHeader";
import type { PackageWithCount, TariffWithCount } from "../api/types";

export function PackagesPage() {
  const { data: packages, isLoading: packagesLoading } = usePackages();
  const { data: tariffs, isLoading: tariffsLoading } = useTariffs();
  const { showToast } = useToast();

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

  // Sorted tariffs
  const sortedTariffs = useMemo(() => {
    if (!tariffs) return [];
    return [...tariffs].sort((a, b) => {
      const dir = tariffSort.sortDir === "asc" ? 1 : -1;
      if (tariffSort.sortBy === "name") return dir * a.name.localeCompare(b.name);
      if (tariffSort.sortBy === "description") return dir * (a.description || "").localeCompare(b.description || "");
      if (tariffSort.sortBy === "package_count") return dir * (a.package_count - b.package_count);
      return 0;
    });
  }, [tariffs, tariffSort.sortBy, tariffSort.sortDir]);

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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-900">Packages</h2>
            <Button size="sm" onClick={openAddPkg}>+ Add</Button>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 resizable-table" style={{ width: "100%" }}>
              <thead className="bg-slate-50">
                <tr>
                  <ResizableHeader colKey="name" width={pkgResize.widths.name} onResize={pkgResize.onResize}>
                    <SortableHeader label="Name" field="name" sortBy={pkgSort.sortBy} sortDir={pkgSort.sortDir} onSort={pkgSort.toggleSort} />
                  </ResizableHeader>
                  <ResizableHeader colKey="description" width={pkgResize.widths.description} onResize={pkgResize.onResize}>
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
              <tbody className="bg-white divide-y divide-slate-200">
                {sortedPackages.length === 0 ? (
                  <EmptyState message="No packages yet" colSpan={4} />
                ) : (
                  sortedPackages.map((p) => (
                    <tr key={p.id}>
                      <td className="px-6 py-3"><div className="font-medium">{p.name}</div></td>
                      <td className="px-6 py-3"><div className="text-sm text-slate-500">{p.description || "-"}</div></td>
                      <td className="px-6 py-3"><span className="text-slate-600">{p.channel_count}</span></td>
                      <td className="px-6 py-3">
                        <div className="flex items-center gap-1">
                          <Button size="sm" variant="secondary" onClick={() => openEditPkg(p)}>Edit</Button>
                          <Button size="sm" variant="danger" onClick={() => setDeletePkgTarget(p)}>Delete</Button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>

        <Card>
          <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-900">Tariffs</h2>
            <Button size="sm" onClick={openAddTariff}>+ Add</Button>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 resizable-table" style={{ width: "100%" }}>
              <thead className="bg-slate-50">
                <tr>
                  <ResizableHeader colKey="name" width={tariffResize.widths.name} onResize={tariffResize.onResize}>
                    <SortableHeader label="Name" field="name" sortBy={tariffSort.sortBy} sortDir={tariffSort.sortDir} onSort={tariffSort.toggleSort} />
                  </ResizableHeader>
                  <ResizableHeader colKey="description" width={tariffResize.widths.description} onResize={tariffResize.onResize}>
                    <SortableHeader label="Description" field="description" sortBy={tariffSort.sortBy} sortDir={tariffSort.sortDir} onSort={tariffSort.toggleSort} />
                  </ResizableHeader>
                  <ResizableHeader colKey="packages" width={tariffResize.widths.packages} onResize={tariffResize.onResize} className="w-28">
                    <SortableHeader label="Packages" field="package_count" sortBy={tariffSort.sortBy} sortDir={tariffSort.sortDir} onSort={tariffSort.toggleSort} />
                  </ResizableHeader>
                  <ResizableHeader colKey="actions" width={tariffResize.widths.actions} onResize={tariffResize.onResize} className="w-40" minWidth={160}>
                    Actions
                  </ResizableHeader>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-200">
                {sortedTariffs.length === 0 ? (
                  <EmptyState message="No tariffs yet" colSpan={4} />
                ) : (
                  sortedTariffs.map((t) => (
                    <tr key={t.id}>
                      <td className="px-6 py-3"><div className="font-medium">{t.name}</div></td>
                      <td className="px-6 py-3"><div className="text-sm text-slate-500">{t.description || "-"}</div></td>
                      <td className="px-6 py-3"><span className="text-slate-600">{t.package_count}</span></td>
                      <td className="px-6 py-3">
                        <div className="flex items-center gap-1">
                          <Button size="sm" variant="secondary" onClick={() => openEditTariff(t)}>Edit</Button>
                          <Button size="sm" variant="danger" onClick={() => setDeleteTariffTarget(t)}>Delete</Button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
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
              <div className="mt-2 max-h-48 overflow-y-auto divide-y rounded-md border border-slate-200">
                {pkgChannels.length === 0 ? (
                  <div className="px-3 py-3 text-sm text-slate-500">No channels assigned.</div>
                ) : (
                  [...pkgChannels]
                    .sort((a, b) => {
                      const na = (a.display_name || a.stream_name || a.tvg_name || "").toLowerCase();
                      const nb = (b.display_name || b.stream_name || b.tvg_name || "").toLowerCase();
                      return na.localeCompare(nb);
                    })
                    .map((ch) => {
                      const primary = ch.display_name || ch.stream_name || ch.tvg_name || `Channel ${ch.id}`;
                      const secondary =
                        ch.display_name && ch.stream_name && ch.display_name !== ch.stream_name
                          ? ch.stream_name
                          : ch.tvg_name || "";
                      return (
                        <div key={ch.id} className="flex items-center justify-between px-3 py-2">
                          <div>
                            <div className="text-sm text-slate-900">{primary}</div>
                            {secondary && <div className="text-xs text-slate-500">{secondary}</div>}
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
            <p className="text-sm text-slate-500">Note: Channels are assigned from the Channels page.</p>
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
            <div className="max-h-48 space-y-2 overflow-y-auto rounded-md border border-slate-200 p-2">
              {(packages || []).map((p) => (
                <label key={p.id} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={selectedPkgIds.includes(p.id)}
                    onChange={() => togglePkgId(p.id)}
                    className="rounded border-slate-300 text-sky-600 focus:ring-sky-500"
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
