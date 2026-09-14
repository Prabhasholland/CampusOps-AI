import { Navigate, Route, Routes } from "react-router-dom";
import IntakePage from "./pages/IntakePage";
import ConfirmationPage from "./pages/ConfirmationPage";
import DashboardPage from "./pages/DashboardPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<IntakePage />} />
      <Route path="/confirmation" element={<ConfirmationPage />} />
      <Route path="/dashboard" element={<DashboardPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
