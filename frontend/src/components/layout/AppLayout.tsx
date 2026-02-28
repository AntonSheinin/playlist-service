import { Outlet } from "react-router-dom";
import { NavBar } from "./NavBar";
import { ToastContainer } from "../ui/ToastContainer";

export function AppLayout() {
  return (
    <div className="min-h-screen">
      <NavBar />
      <main className="mx-auto w-full max-w-screen-2xl px-4 py-6 md:px-6 md:py-8">
        <Outlet />
      </main>
      <ToastContainer />
    </div>
  );
}
