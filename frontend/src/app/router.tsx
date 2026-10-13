import React, { Suspense } from "react";
import { BrowserRouter, Route, Routes, Navigate } from "react-router";
import { AppLayout } from "../components/layout/AppLayout";
import { LandingPage } from "../features/landing/LandingPage";
import { LoginPage } from "../features/auth/LoginPage";
import { RegisterPage } from "../features/auth/RegisterPage";
import { DashboardPage } from "../features/repos/DashboardPage";

// Lazy-loaded routes for performance & code-splitting (§11, §20)
const OverviewPage = React.lazy(() =>
  import("../features/overview/OverviewPage").then((m) => ({ default: m.OverviewPage }))
);
const ChatPage = React.lazy(() =>
  import("../features/chat/ChatPage").then((m) => ({ default: m.ChatPage }))
);
const ExplorerPage = React.lazy(() =>
  import("../features/explorer/ExplorerPage").then((m) => ({ default: m.ExplorerPage }))
);
const GraphPage = React.lazy(() =>
  import("../features/graph/GraphPage").then((m) => ({ default: m.GraphPage }))
);
const SearchPage = React.lazy(() =>
  import("../features/search/SearchPage").then((m) => ({ default: m.SearchPage }))
);
const ReviewsPage = React.lazy(() =>
  import("../features/reviews/ReviewsPage").then((m) => ({ default: m.ReviewsPage }))
);
const EvaluationPage = React.lazy(() =>
  import("../features/evaluation/EvaluationPage").then((m) => ({ default: m.EvaluationPage }))
);
const SettingsPage = React.lazy(() =>
  import("../features/settings/SettingsPage").then((m) => ({ default: m.SettingsPage }))
);
const AdminPage = React.lazy(() =>
  import("../features/admin/AdminPage").then((m) => ({ default: m.AdminPage }))
);

const RouteLoadingFallback = () => (
  <div className="flex h-[calc(100vh-4rem)] w-full items-center justify-center bg-zinc-50">
    <div className="flex flex-col items-center gap-3">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent" />
      <span className="font-mono text-xs text-zinc-500">Loading view...</span>
    </div>
  </div>
);

export const AppRouter: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* Authenticated Application Shell */}
        <Route path="/app" element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route
            path="repos/:repoId/overview"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <OverviewPage />
              </Suspense>
            }
          />
          <Route
            path="repos/:repoId/chat"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <ChatPage />
              </Suspense>
            }
          />
          <Route
            path="repos/:repoId/chat/:conversationId"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <ChatPage />
              </Suspense>
            }
          />
          <Route
            path="repos/:repoId/explorer"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <ExplorerPage />
              </Suspense>
            }
          />
          <Route
            path="repos/:repoId/graph"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <GraphPage />
              </Suspense>
            }
          />
          <Route
            path="repos/:repoId/search"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <SearchPage />
              </Suspense>
            }
          />
          <Route
            path="repos/:repoId/reviews"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <ReviewsPage />
              </Suspense>
            }
          />
          <Route
            path="evaluation"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <EvaluationPage />
              </Suspense>
            }
          />
          <Route
            path="evaluation/runs/:runId"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <EvaluationPage />
              </Suspense>
            }
          />
          <Route
            path="settings"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <SettingsPage />
              </Suspense>
            }
          />
          <Route
            path="admin"
            element={
              <Suspense fallback={<RouteLoadingFallback />}>
                <AdminPage />
              </Suspense>
            }
          />
        </Route>

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
};
