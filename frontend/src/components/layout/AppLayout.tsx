import { Outlet } from "react-router-dom";
import { NavBar } from "./NavBar";
import { ToastContainer } from "../ui/ToastContainer";

export function AppLayout() {
  return (
    <div className="min-h-screen bg-background">
      <NavBar />
      <main className="px-4 pb-8 pt-4 md:ml-[248px] md:px-6 md:pb-10 md:pt-6">
        <Outlet />
      </main>
      <ToastContainer />
    </div>
  );
}
