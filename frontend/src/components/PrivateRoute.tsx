import { useEffect, useState } from "react";
import { Navigate, Outlet } from "react-router-dom";
import { authApi } from "@/api/auth";

export default function PrivateRoute() {
  const [state, setState] = useState<"checking" | "authed" | "unauthed">("checking");

  useEffect(() => {
    authApi
      .me()
      .then(() => setState("authed"))
      .catch(() => setState("unauthed"));
  }, []);

  if (state === "checking") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <div className="text-gray-400 text-sm">Loading…</div>
      </div>
    );
  }

  return state === "authed" ? <Outlet /> : <Navigate to="/login" replace />;
}
