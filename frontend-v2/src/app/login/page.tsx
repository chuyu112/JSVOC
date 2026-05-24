import { Suspense } from "react";
import LoginForm from "./LoginForm";

export default function LoginPage() {
  return (
    <section className="auth-page">
      {/* Left Panel: Branding */}
      <div className="hidden md:flex flex-col items-center justify-center flex-1 max-w-[500px]">
        <div className="text-center">
          <div className="brand-token brand-token-lg mx-auto mb-6" aria-hidden="true" />
          <h2 className="text-3xl font-bold text-[#f5f5f5] tracking-tight mb-3">短视频运营中心</h2>
          <p className="text-[#7a8a82] text-base leading-relaxed max-w-sm">
            Operation Center
          </p>
        </div>
      </div>

      {/* Right Panel: Form */}
      <Suspense fallback={<div className="auth-panel flex items-center justify-center"><div className="text-[#9ca3af] text-sm">加载中...</div></div>}>
        <LoginForm />
      </Suspense>
    </section>
  );
}
