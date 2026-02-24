import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { AuthProvider } from "./contexts/AuthContext";
import { ToastProvider } from "./contexts/ToastContext";
import { ProtectedRoute } from "./components/layout/ProtectedRoute";
import { AppLayout } from "./components/layout/AppLayout";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { ChannelsPage } from "./pages/ChannelsPage";
import { GroupsPage } from "./pages/GroupsPage";
import { PackagesPage } from "./pages/PackagesPage";
import { UsersListPage } from "./pages/UsersListPage";
import { UserDetailPage } from "./pages/UserDetailPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <ErrorBoundary>
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route element={<ProtectedRoute />}>
                <Route element={<AppLayout />}>
                  <Route path="/" element={<DashboardPage />} />
                  <Route path="/channels" element={<ChannelsPage />} />
                  <Route path="/groups" element={<GroupsPage />} />
                  <Route path="/packages" element={<PackagesPage />} />
                  <Route path="/users" element={<UsersListPage />} />
                  <Route path="/users/new" element={<UserDetailPage />} />
                  <Route path="/users/:userId" element={<UserDetailPage />} />
                </Route>
              </Route>
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </ToastProvider>
    </QueryClientProvider>
    </ErrorBoundary>
  );
}
