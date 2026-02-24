import { Outlet } from "react-router-dom";
import { NavBar } from "./NavBar";
import { ToastContainer } from "../ui/ToastContainer";

export function AppLayout() {
  return (
    <div className="min-h-screen bg-gray-100">
      <NavBar />
      <main className="container mx-auto px-4 py-6">
        <Outlet />
      </main>
      <ToastContainer />
    </div>
  );
}
