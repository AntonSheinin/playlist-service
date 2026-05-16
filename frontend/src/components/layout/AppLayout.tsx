import { Outlet } from "react-router-dom";
import { Box } from "@mui/material";
import { NavBar } from "./NavBar";
import { ToastContainer } from "../ui/ToastContainer";
import { drawerWidth } from "../../theme";

export function AppLayout() {
  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
      <NavBar />
      <Box
        component="main"
        sx={{
          width: { md: `calc(100% - ${drawerWidth}px)` },
          ml: { md: `${drawerWidth}px` },
          px: { xs: 2, md: 3 },
          py: { xs: 2, md: 3 },
        }}
      >
        <Outlet />
      </Box>
      <ToastContainer />
    </Box>
  );
}
