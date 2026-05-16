import { useState } from "react";
import { Link as RouterLink, useLocation } from "react-router-dom";
import {
  AppBar,
  Avatar,
  Box,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
  useMediaQuery,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import DashboardIcon from "@mui/icons-material/Dashboard";
import GroupsIcon from "@mui/icons-material/FolderCopy";
import InventoryIcon from "@mui/icons-material/Inventory2";
import LiveTvIcon from "@mui/icons-material/LiveTv";
import LogoutIcon from "@mui/icons-material/Logout";
import MenuIcon from "@mui/icons-material/Menu";
import PeopleIcon from "@mui/icons-material/People";
import { useAuth } from "../../hooks/useAuth";
import { drawerWidth } from "../../theme";

const navLinks = [
  { to: "/", label: "Dashboard", key: "dashboard", icon: <DashboardIcon fontSize="small" /> },
  { to: "/channels", label: "Channels", key: "channels", icon: <LiveTvIcon fontSize="small" /> },
  { to: "/groups", label: "Groups", key: "groups", icon: <GroupsIcon fontSize="small" /> },
  { to: "/packages", label: "Packages & Tariffs", key: "packages", icon: <InventoryIcon fontSize="small" /> },
  { to: "/users", label: "Users", key: "users", icon: <PeopleIcon fontSize="small" /> },
];

function isActive(key: string, pathname: string): boolean {
  if (key === "dashboard") return pathname === "/";
  return pathname.startsWith(`/${key}`);
}

export function NavBar() {
  const { admin, logout } = useAuth();
  const { pathname } = useLocation();
  const theme = useTheme();
  const desktop = useMediaQuery(theme.breakpoints.up("md"));
  const [mobileOpen, setMobileOpen] = useState(false);

  const drawer = (
    <Box sx={{ display: "flex", minHeight: "100%", flexDirection: "column" }}>
      <Toolbar sx={{ gap: 1.5, minHeight: 64 }}>
        <Avatar src="/media/rutv-logo.png" alt="RUTV logo" variant="rounded" sx={{ width: 34, height: 34 }} />
        <Box sx={{ minWidth: 0 }}>
          <Typography noWrap variant="subtitle1" sx={{ fontWeight: 700 }}>
            Playlist Service
          </Typography>
          <Typography noWrap variant="caption" color="text.secondary">
            Admin console
          </Typography>
        </Box>
      </Toolbar>
      <Divider />
      <List dense sx={{ flex: 1, px: 1, py: 1.5 }}>
        {navLinks.map((link) => {
          const active = isActive(link.key, pathname);
          return (
            <ListItemButton
              key={link.key}
              component={RouterLink}
              to={link.to}
              selected={active}
              onClick={() => setMobileOpen(false)}
              sx={{
                mb: 0.5,
                borderRadius: 1,
                "&.Mui-selected": {
                  bgcolor: "#e0f2fe",
                },
              }}
            >
              <ListItemIcon sx={{ minWidth: 36, color: active ? "primary.main" : "text.secondary" }}>
                {link.icon}
              </ListItemIcon>
              <ListItemText
                primary={<Typography sx={{ fontSize: 14, fontWeight: active ? 700 : 500 }}>{link.label}</Typography>}
              />
            </ListItemButton>
          );
        })}
      </List>
      <Divider />
      <Box sx={{ p: 1.5 }}>
        <Typography noWrap variant="body2" color="text.secondary" sx={{ px: 1, mb: 1 }}>
          {admin?.username}
        </Typography>
        <ListItemButton onClick={() => void logout()} sx={{ borderRadius: 1, color: "error.main" }}>
          <ListItemIcon sx={{ minWidth: 36, color: "error.main" }}>
            <LogoutIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText primary={<Typography sx={{ fontSize: 14, fontWeight: 600 }}>Logout</Typography>} />
        </ListItemButton>
      </Box>
    </Box>
  );

  return (
    <>
      {!desktop && (
        <AppBar position="sticky" color="inherit" elevation={0} sx={{ borderBottom: 1, borderColor: "divider" }}>
          <Toolbar variant="dense">
            <IconButton edge="start" color="inherit" onClick={() => setMobileOpen(true)} aria-label="Open menu">
              <MenuIcon />
            </IconButton>
            <Typography variant="subtitle1" sx={{ ml: 1, fontWeight: 700 }}>
              Playlist Service
            </Typography>
          </Toolbar>
        </AppBar>
      )}
      <Box component="nav" aria-label="Main navigation">
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: "block", md: "none" },
            "& .MuiDrawer-paper": { boxSizing: "border-box", width: drawerWidth },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          open
          sx={{
            display: { xs: "none", md: "block" },
            "& .MuiDrawer-paper": { boxSizing: "border-box", width: drawerWidth },
          }}
        >
          {drawer}
        </Drawer>
      </Box>
    </>
  );
}
