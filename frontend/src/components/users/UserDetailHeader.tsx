import { Link } from "react-router-dom";
import { Button } from "../ui/Button";
import { PageHeader } from "../ui/PageHeader";
import { Input } from "../ui/Input";

interface UserDetailHeaderProps {
  isEdit: boolean;
  userName?: string;
  playlistUrl: string;
  onOpenPreview: () => void;
  onDownloadPlaylist: () => void;
}

export function UserDetailHeader({
  isEdit,
  userName,
  playlistUrl,
  onOpenPreview,
  onDownloadPlaylist,
}: UserDetailHeaderProps) {
  return (
    <div className="space-y-3">
      <Link to="/users" className="inline-flex text-sm text-muted-foreground hover:text-foreground">
        &larr; Back to Users
      </Link>
      <PageHeader
        title={isEdit ? `Edit User${userName ? `: ${userName}` : ""}` : "New User"}
        actions={
          isEdit ? (
            <div className="flex w-full flex-col gap-2 md:w-auto md:flex-row md:items-end">
              <div className="min-w-[16rem] md:min-w-[22rem]">
                <Input
                  label="Playlist URL"
                  readOnly
                  value={playlistUrl}
                  className="bg-muted text-xs font-mono text-muted-foreground"
                />
              </div>
              <Button variant="secondary" type="button" onClick={onOpenPreview}>
                Preview Playlist
              </Button>
              <Button type="button" onClick={onDownloadPlaylist}>
                Download Playlist
              </Button>
            </div>
          ) : undefined
        }
      />
    </div>
  );
}
