import { Outlet } from "react-router-dom";
import Navbar from "../components/Navbar";

export default function DashboardLayout() {
  return (
    <div className="min-h-screen bg-bg bg-mesh">
      <Navbar />
      <Outlet />
    </div>
  );
}