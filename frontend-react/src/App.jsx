import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import DashboardLayout from "./layouts/DashboardLayout";
import FollowUps from "./pages/FollowUps";
import Events from "./pages/Events";
import Recommendations from "./pages/Recommendations";
import Opportunities from "./pages/Opportunities";
import RelationshipScores from "./pages/RelationshipScores";
import Analytics from "./pages/Analytics";

import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Generate from "./pages/Generate";
import FactCheck from "./pages/FactCheck";
import History from "./pages/History";
import FeedbackHistory from "./pages/FeedbackHistory";
import Contacts from "./pages/Contacts";
import ContactProfile from "./pages/ContactProfile";

function AppRoutes() {
  const { isAuthenticated } = useAuth();

  return (
    <Routes>
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <Login />}
      />

      <Route
        element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/contacts" element={<Contacts />} />
        <Route path="/contacts/:id" element={<ContactProfile />} />
        <Route path="/generate" element={<Generate />} />
        <Route path="/fact-check" element={<FactCheck />} />
        <Route path="/history" element={<History />} />
        <Route path="/feedback-history" element={<FeedbackHistory />} />
        <Route path="/follow-ups" element={<FollowUps />} />
        <Route path="/events" element={<Events />} />
        <Route path="/recommendations" element={<Recommendations />} />
        <Route path="/opportunities" element={<Opportunities />} />
        <Route path="/relationship-scores" element={<RelationshipScores />} />
        <Route path="/analytics" element={<Analytics />} />
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
