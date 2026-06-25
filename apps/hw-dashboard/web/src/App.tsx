import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Overview } from "./views/Overview";
import { ComponentExplorer } from "./views/ComponentExplorer";
import { PriceForecast } from "./views/PriceForecast";
import { EvidenceDrawer } from "./views/EvidenceDrawer";

type Tab = "overview" | "components" | "price" | "evidence";

const TABS: Array<{
  id: Tab;
  label: string;
  icon: string;
  shortLabel: string;
}> = [
  { id: "overview", label: "Overview", icon: "◈", shortLabel: "Overview" },
  {
    id: "components",
    label: "Component Explorer",
    icon: "⊞",
    shortLabel: "Components",
  },
  { id: "price", label: "Price & Forecast", icon: "⟁", shortLabel: "Price" },
  { id: "evidence", label: "Evidence", icon: "◉", shortLabel: "Evidence" },
];

function TabView({ tab }: { tab: Tab }) {
  switch (tab) {
    case "overview":
      return <Overview />;
    case "components":
      return <ComponentExplorer />;
    case "price":
      return <PriceForecast />;
    case "evidence":
      return <EvidenceDrawer />;
  }
}

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>("overview");

  return (
    <div className="app-shell">
      <header className="site-header" role="banner">
        <div className="header-inner">
          <div>
            <h1 className="wordmark" aria-label="Hardware Dashboard">
              HW//DASH
            </h1>
            <span className="wordmark-sub">UPGRADE INTELLIGENCE</span>
          </div>

          <nav
            className="nav-tabs"
            role="navigation"
            aria-label="Main navigation"
          >
            {TABS.map((tab) => (
              <button
                key={tab.id}
                className={`nav-tab ${activeTab === tab.id ? "active" : ""}`}
                onClick={() => setActiveTab(tab.id)}
                aria-current={activeTab === tab.id ? "page" : undefined}
                aria-label={tab.label}
              >
                <span className="nav-tab-icon" aria-hidden="true">
                  {tab.icon}
                </span>
                <span>{tab.shortLabel}</span>
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main
        id="main-content"
        className="main-content"
        role="main"
        tabIndex={-1}
      >
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
          >
            <TabView tab={activeTab} />
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}
