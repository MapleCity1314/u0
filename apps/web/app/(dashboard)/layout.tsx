import AppNavigation from "@/components/navigation";

export default function DashboardLayoutWrapper({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen text-zinc-50 transition-colors duration-300">
      <AppNavigation />

      <main className="mx-auto flex w-full max-w-7xl flex-col px-4 py-6 pb-24 lg:pl-28 lg:py-8 lg:pb-8">
        {children}
      </main>
    </div>
  );
}
