import { useState } from "react";
import Layout from "./components/Layout";
import ClientsPage from "./pages/ClientsPage";
import ExecutionsPage from "./pages/ExecutionsPage";
import LogsPage from "./pages/LogsPage";
import MonetizationPage from "./pages/MonetizationPage";
import OverviewPage from "./pages/OverviewPage";
import { useCockpitData } from "./hooks/useCockpitData";

export default function App() {
  const [page, setPage] = useState("Overview");
  const { data, loading, logs, createClient } = useCockpitData();
  const pages = {
    Overview: <OverviewPage data={data} loading={loading} onNavigate={setPage} />,
    Clients: <ClientsPage data={data} loading={loading} onCreate={createClient} />,
    Executions: <ExecutionsPage data={data} loading={loading} />,
    Monetization: <MonetizationPage data={data} loading={loading} />,
    Logs: <LogsPage logs={logs} loading={loading} />,
  };
  return <Layout page={page} onNavigate={setPage}>{pages[page]}</Layout>;
}
