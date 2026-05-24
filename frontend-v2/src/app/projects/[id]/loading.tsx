export default function ProjectRouteLoading() {
  return (
    <section className="page-section">
      <div className="section-header">
        <div>
          <div className="h-3 w-20 rounded bg-white/[0.08]" />
          <div className="mt-3 h-8 w-56 rounded bg-white/[0.08]" />
        </div>
        <div className="h-9 w-24 rounded-md bg-white/[0.08]" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-6">
        <div className="glass rounded-[1rem] p-5 space-y-4">
          <div className="h-4 w-20 rounded bg-white/[0.08]" />
          <div className="space-y-2">
            <div className="h-9 rounded-[0.625rem] bg-white/[0.06]" />
            <div className="h-9 rounded-[0.625rem] bg-white/[0.06]" />
            <div className="h-9 rounded-[0.625rem] bg-white/[0.06]" />
          </div>
        </div>

        <div className="glass rounded-[1rem] p-5 md:p-6 space-y-4">
          <div className="h-4 w-24 rounded bg-white/[0.08]" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="h-14 rounded-md bg-white/[0.05]" />
            <div className="h-14 rounded-md bg-white/[0.05]" />
            <div className="h-20 rounded-md bg-white/[0.05] md:col-span-2" />
            <div className="h-20 rounded-md bg-white/[0.05] md:col-span-2" />
          </div>
        </div>
      </div>
    </section>
  );
}
