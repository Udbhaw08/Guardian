import { useOutlet } from "react-router-dom";
import { TopNav } from "./TopNav";

export function Layout() {
  const outlet = useOutlet();

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col font-sans selection:bg-primary/20 selection:text-primary">
      {/* Sleek Enterprise Top Navigation Bar */}
      <header className="sticky top-0 z-30 w-full border-b border-border/80 bg-background/80 backdrop-blur-md">
        <TopNav />
      </header>

      {/* Main Content Area */}
      <main className="flex-1 w-full max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-6 animate-fade-in">
        {outlet}
      </main>
    </div>
  );
}
