import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { cn } from "../../utils/cn";

const navLinks = [
  { to: "/", label: "Dashboard", key: "dashboard" },
  { to: "/channels", label: "Channels", key: "channels" },
  { to: "/groups", label: "Groups", key: "groups" },
  { to: "/packages", label: "Packages & Tariffs", key: "packages" },
  { to: "/users", label: "Users", key: "users" },
];

function isActive(key: string, pathname: string): boolean {
  if (key === "dashboard") return pathname === "/";
  return pathname.startsWith(`/${key}`);
}

export function NavBar() {
  const { admin, logout } = useAuth();
  const { pathname } = useLocation();

  return (
    <nav className="bg-white shadow-sm sticky top-0 z-30">
      <div className="container mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div className="flex items-center">
            <Link to="/" className="flex items-center space-x-2 text-xl font-bold text-gray-800">
              <img src="/media/rutv-logo.png" alt="RUTV logo" className="h-8 w-8 object-contain" />
              <span>Playlist Service</span>
            </Link>
          </div>

          {/* Navigation links */}
          <div className="hidden md:flex items-center space-x-4">
            {navLinks.map((link) => (
              <Link
                key={link.key}
                to={link.to}
                className={cn(
                  "px-3 py-2 rounded-md text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-100",
                  isActive(link.key, pathname) && "bg-gray-100 text-gray-900"
                )}
              >
                {link.label}
              </Link>
            ))}
          </div>

          {/* User menu */}
          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-600">{admin?.username}</span>
            <button
              onClick={logout}
              className="text-sm text-red-600 hover:text-red-800"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}
