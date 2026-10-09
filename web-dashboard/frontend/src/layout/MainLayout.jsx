import Sidebar from "../components/Sidebar";
import { Outlet } from "react-router-dom";

export default function MainLayout() {
  return (
    <div className="flex min-h-screen w-full bg-canvas">
      <Sidebar />
      <div className="min-w-0 flex-1 px-4 py-5 md:px-6">
        <Outlet />
      </div>
    </div>
  );
}
