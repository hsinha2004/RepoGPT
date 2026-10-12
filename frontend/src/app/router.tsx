import React from "react";
import { BrowserRouter, Route, Routes, Navigate } from "react-router";
import { AppLayout } from "../components/layout/AppLayout";
import { LandingPage } from "../features/landing/LandingPage";
import { LoginPage } from "../features/auth/LoginPage";
import { RegisterPage } from "../features/auth/RegisterPage";
import { DashboardPage } from "../features/repos/DashboardPage";
import { OverviewPage } from "../features/overview/OverviewPage";
import { ChatPage } from "../features/chat/ChatPage";
import { ExplorerPage } from "../features/explorer/ExplorerPage";
import { GraphPage } from "../features/graph/GraphPage";
import { SearchPage } from "../features/search/SearchPage";
import { ReviewsPage } from "../features/reviews/ReviewsPage";
import { EvaluationPage } from "../features/evaluation/EvaluationPage";
import { SettingsPage } from "../features/settings/SettingsPage";
import { AdminPage } from "../features/admin/AdminPage";

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
          <Route path="repos/:repoId/overview" element={<OverviewPage />} />
          <Route path="repos/:repoId/chat" element={<ChatPage />} />
          <Route path="repos/:repoId/chat/:conversationId" element={<ChatPage />} />
          <Route path="repos/:repoId/explorer" element={<ExplorerPage />} />
          <Route path="repos/:repoId/graph" element={<GraphPage />} />
          <Route path="repos/:repoId/search" element={<SearchPage />} />
          <Route path="repos/:repoId/reviews" element={<ReviewsPage />} />
          <Route path="evaluation" element={<EvaluationPage />} />
          <Route path="evaluation/runs/:runId" element={<EvaluationPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="admin" element={<AdminPage />} />
        </Route>

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
};
