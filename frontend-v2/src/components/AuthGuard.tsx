"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "./AuthProvider";

const PUBLIC_PATHS = ["/login"];

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const auth = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const isPublic = PUBLIC_PATHS.includes(pathname ?? "");
  const isRedirecting =
    auth.checked &&
    ((!auth.isAuthenticated && !isPublic) || (auth.isAuthenticated && pathname === "/login"));

  useEffect(() => {
    if (!auth.checked) return;

    if (!auth.isAuthenticated && !isPublic) {
      const redirect = pathname && pathname !== "/" ? `?redirect=${encodeURIComponent(pathname)}` : "";
      router.replace(`/login${redirect}`);
    } else if (auth.isAuthenticated && pathname === "/login") {
      router.replace("/projects");
    }
  }, [auth.checked, auth.isAuthenticated, isPublic, pathname, router]);

  if (!auth.checked) {
    return <>{children}</>;
  }

  if (isRedirecting && !isPublic) {
    return (
      <div className="flex items-center justify-center min-h-[100dvh]">
        <div className="text-[#9ca3af] text-sm">加载中...</div>
      </div>
    );
  }

  return <>{children}</>;
}
