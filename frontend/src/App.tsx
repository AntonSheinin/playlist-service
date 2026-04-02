import { Suspense, lazy } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { AuthProvider } from "./contexts/AuthContext";
import { ToastProvider } from "./contexts/ToastContext";
import { ProtectedRoute } from "./components/layout/ProtectedRoute";
import { AppLayout } from "./components/layout/AppLayout";
import { Spinner } from "./components/ui/Spinner";

const LoginPage = lazy(() =>
  import("./pages/LoginPage").then((module) => ({ default: module.LoginPage }))
);
const DashboardPage = lazy(() =>
  import("./pages/DashboardPage").then((module) => ({ default: module.DashboardPage }))
);
const ChannelsPage = lazy(() =>
  import("./pages/ChannelsPage").then((module) => ({ default: module.ChannelsPage }))
);
const GroupsPage = lazy(() =>
  import("./pages/GroupsPage").then((module) => ({ default: module.GroupsPage }))
);
const PackagesPage = lazy(() =>
  import("./pages/PackagesPage").then((module) => ({ default: module.PackagesPage }))
);
const UsersListPage = lazy(() =>
  import("./pages/UsersListPage").then((module) => ({ default: module.UsersListPage }))
);
const UserDetailPage = lazy(() =>
  import("./pages/UserDetailPage").then((module) => ({ default: module.UserDetailPage }))
);

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
              <Suspense
                fallback={
                  <div className="flex min-h-screen items-center justify-center">
                    <Spinner />
                  </div>
                }
              >
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
              </Suspense>
            </BrowserRouter>
          </AuthProvider>
        </ToastProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
