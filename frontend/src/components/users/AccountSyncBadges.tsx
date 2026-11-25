import { Badge } from "../ui/Badge";

interface AccountSyncBadgesProps {
  authSynced: boolean;
  portalAllowed: boolean;
  portalSynced: boolean;
}

export function AccountSyncBadges({ authSynced, portalAllowed, portalSynced }: AccountSyncBadgesProps) {
  return (
    <div className="flex flex-wrap gap-1.5">
      <Badge variant={authSynced ? "green" : "yellow"}>
        Auth · {authSynced ? "Synced" : "Not synced"}
      </Badge>
      {portalAllowed && (
        <Badge variant={portalSynced ? "green" : "yellow"}>
          Portal · {portalSynced ? "Synced" : "Not synced"}
        </Badge>
      )}
    </div>
  );
}
