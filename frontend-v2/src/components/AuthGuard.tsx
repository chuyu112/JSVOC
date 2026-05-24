"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "./AuthProvider";

const PUBLIC_PATHS = ["/login"];

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const auth = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!auth.checked) return;

    const isPublic = PUBLIC_PATHS.includes(pathname ?? "");

    if (!auth.isAuthenticated && !isPublic) {
      const redirect = pathname && pathname !== "/" ? `?redirect=${encodeURIComponent(pathname)}` : "";
      router.replace(`/login${redirect}`);
    } else if (auth.isAuthenticated && pathname === "/login") {
      router.replace("/projects");
    } else {
      setReady(true);
    }
  }, [auth.checked, auth.isAuthenticated, pathname, router]);

  if (!ready && !PUBLIC_PATHS.includes(pathname ?? "")) {
    return (
      <div className="flex items-center justify-center min-h-[100dvh]">
        <div className="text-[#9ca3af] text-sm">加载中...</div>
      </div>
    );
  }

  return <>{children}</>;
}
