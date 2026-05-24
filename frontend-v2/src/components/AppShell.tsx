"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "./AuthProvider";
import { getCreditBalance } from "@/lib/api/credits";
// ThemeSwitcher moved to /settings page

const globalNavItems = [
  { label: "项目档案", mobileLabel: "项目", to: "/projects" },
  { label: "AI聊天", mobileLabel: "聊天", to: "/ai-chat" },
  { label: "AI生图", mobileLabel: "生图", to: "/images" },
  { label: "AI生视频", mobileLabel: "视频", to: "/videos" },
  { label: "数字资产", mobileLabel: "资产", to: "/assets" },
  { label: "AI爆款拆解", mobileLabel: "爆款", to: "/hot-videos" },
  { label: "AI数字人", mobileLabel: "数字人", to: "/digital-human" },
];

function isNavItemActive(pathname: string | null, item: (typeof globalNavItems)[number]) {
  if (!pathname) return false;

  if (item.to === "/projects") {
    return pathname === "/projects" || pathname === "/projects/new" || pathname.startsWith("/projects/");
  }

  return pathname === item.to || pathname.startsWith(`${item.to}/`);
}

function Brand() {
  return (
    <Link href="/projects" className="app-brand inline-flex items-center gap-3 text-[#f5f5f5]">
      <span className="brand-token" aria-hidden="true" />
      <span className="app-brand-copy">
        <strong className="app-brand-title block text-[16px] font-[680] tracking-[-0.01em]">短视频运营中心</strong>
        <small className="app-brand-subtitle block mt-[2px] text-[12px] font-medium text-[#7a8a82]">Operation Center</small>
      </span>
    </Link>
  );
}

function NavLink({
  href,
  active,
  children,
}: {
  href: string;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={`inline-flex items-center min-h-[36px] px-2.5 lg:px-3 xl:px-4 rounded-[0.75rem] font-medium text-[14px] transition-all duration-300 ${
        active
          ? "border border-[rgba(90,155,130,0.2)] bg-[rgba(90,155,130,0.15)] text-[#4a856e] font-[620]"
          : "border border-transparent text-[#7a8a82] hover:text-[#f5f5f5] hover:bg-[rgba(255,255,255,0.06)]"
      }`}
    >
      {children}
    </Link>
  );
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const auth = useAuth();
  const pathname = usePathname();
  const [creditBalance, setCreditBalance] = useState<number | null>(null);

  const settingsReturnPath = pathname && pathname !== "/settings" ? pathname : "/projects";
  const settingsHref = `/settings?returnTo=${encodeURIComponent(settingsReturnPath)}`;

  useEffect(() => {
    if (!auth.isAuthenticated) {
      return;
    }

    let cancelled = false;
    getCreditBalance()
      .then((account) => {
        if (!cancelled) setCreditBalance(account.balance);
      })
      .catch(() => {
        if (!cancelled) setCreditBalance(auth.user?.credit_balance ?? null);
      });

    return () => {
      cancelled = true;
    };
  }, [auth.isAuthenticated, auth.user?.credit_balance, pathname]);

  const isLoginPage = pathname === "/login";

  return (
    <div className="flex flex-col min-h-[100dvh]">
      {!isLoginPage && (
        <header className="app-header sticky top-0 z-20 flex flex-col items-center justify-between h-auto w-full px-6 glass-strong">
          <div className="app-header-row flex items-center justify-between gap-5 w-[min(1400px,100%)] min-h-[60px]">
            <Brand />

            {auth.isAuthenticated && (
              <nav className="app-desktop-nav hidden min-w-0 flex-wrap justify-center md:inline-flex items-center gap-[6px] p-0 border-0 bg-transparent text-[#7a8a82] text-[14px] font-medium">
                {globalNavItems.map((item) => (
                  <NavLink
                    key={item.to}
                    href={item.to}
                    active={isNavItemActive(pathname, item)}
                  >
                    {item.label}
                  </NavLink>
                ))}
              </nav>
            )}

            {auth.isAuthenticated && (
              <div className="app-user-actions inline-flex items-center gap-[10px] text-[#b0b0b0]">
                <span
                  className="app-credit-pill hidden sm:inline-flex items-center min-h-[30px] rounded-[999px] border px-3 text-[12px] font-[620]"
                  style={{
                    borderColor: "rgba(127,220,146,0.22)",
                    color: "var(--jade-text-main)",
                    background: "rgba(127,220,146,0.1)",
                  }}
                >
                  {creditBalance ?? auth.user?.credit_balance ?? 0} 积分
                </span>
                <span className="app-user-name max-w-[160px] overflow-hidden text-[14px] font-[580] text-[#f5f5f5] text-ellipsis whitespace-nowrap">
                  {auth.displayName}
                </span>
                <Link
                  href={settingsHref}
                  className="app-settings-btn inline-flex items-center justify-center min-h-[32px] px-2.5 rounded-[0.75rem] border border-[rgba(255,255,255,0.06)] text-[12px] font-medium text-[#7a8a82] transition-all hover:text-[#f5f5f5] hover:bg-[rgba(255,255,255,0.06)]"
                  title="设置"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                </Link>
              </div>
            )}
          </div>
        </header>
      )}

      {!isLoginPage && auth.isAuthenticated && (
        <>
          <details className="mobile-side-drawer mobile-side-drawer-left md:hidden">
            <summary className="mobile-side-trigger" aria-label="打开导航">
              导航
            </summary>
            <nav className="mobile-side-sheet">
              {globalNavItems.map((item) => (
                <Link
                  key={item.to}
                  href={item.to}
                  className={`mobile-side-link ${
                    isNavItemActive(pathname, item) ? "mobile-side-link-active" : ""
                  }`}
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </details>

          <details className="mobile-side-drawer mobile-side-drawer-right md:hidden">
            <summary className="mobile-side-trigger" aria-label="打开账户">
              账户
            </summary>
            <div className="mobile-side-sheet">
              <div className="mobile-account-card">
                <span>{auth.displayName}</span>
                <strong>{creditBalance ?? auth.user?.credit_balance ?? 0} 积分</strong>
              </div>
              <Link
                href={settingsHref}
                className={`mobile-side-link ${pathname === "/settings" ? "mobile-side-link-active" : ""}`}
              >
                用户设置
              </Link>
            </div>
          </details>

          <nav className="mobile-bottom-nav md:hidden" aria-label="底部导航">
            {globalNavItems.map((item) => (
              <Link
                key={item.to}
                href={item.to}
                className={`mobile-bottom-link ${
                  isNavItemActive(pathname, item) ? "mobile-bottom-link-active" : ""
                }`}
              >
                {item.mobileLabel}
              </Link>
            ))}
          </nav>
        </>
      )}

      <main className="app-main flex-1">{children}</main>
    </div>
  );
}
