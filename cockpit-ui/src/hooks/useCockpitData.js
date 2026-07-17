import { useCallback, useEffect, useMemo, useState } from "react";
import { cockpitApi } from "../lib/api";
import { pilotData } from "../fixtures/pilotData";
import { asArray } from "../lib/format";

const PILOT_MODE = import.meta.env.VITE_PILOT_MODE === "true";

const EMPTY = {
  overview: null,
  usage: null,
  billing: null,
  executions: null,
  clients: [],
  clientDetails: {},
};

export function useCockpitData() {
  const [data, setData] = useState(PILOT_MODE ? pilotData : EMPTY);
  const [loading, setLoading] = useState(!PILOT_MODE);

  const refreshAll = useCallback(async () => {
    if (PILOT_MODE) {
      setData(pilotData);
      setLoading(false);
      return;
    }
    setLoading(true);
    const results = await Promise.allSettled([
      cockpitApi.overview(),
      cockpitApi.usage(),
      cockpitApi.billing(),
      cockpitApi.executions(),
      cockpitApi.clients(),
    ]);
    const next = {
      overview: results[0].status === "fulfilled" ? results[0].value : null,
      usage: results[1].status === "fulfilled" ? results[1].value : null,
      billing: results[2].status === "fulfilled" ? results[2].value : null,
      executions: results[3].status === "fulfilled" ? results[3].value : null,
      clients: results[4].status === "fulfilled" ? asArray(results[4].value) : [],
      clientDetails: {},
    };
    const ids = next.clients.map((client) => client.id).filter(Boolean);
    const details = await Promise.allSettled(ids.map((id) => cockpitApi.client(id)));
    ids.forEach((id, index) => {
      if (details[index].status === "fulfilled") next.clientDetails[id] = details[index].value;
    });
    setData(next);
    setLoading(false);
  }, []);

  useEffect(() => {
    refreshAll();
  }, [refreshAll]);

  useEffect(() => {
    if (PILOT_MODE) return undefined;
    const timer = window.setInterval(async () => {
      try {
        const executions = await cockpitApi.executions();
        setData((current) => ({ ...current, executions }));
      } catch {
        // Keep the last successful snapshot when polling fails.
      }
    }, 7000);
    return () => window.clearInterval(timer);
  }, []);

  const logs = useMemo(() => {
    const combined = [
      ...asArray(data.overview?.recent_errors),
      ...asArray(data.overview?.connector_activity),
      ...Object.values(data.clientDetails).flatMap((detail) => asArray(detail?.logs)),
    ];
    const unique = new Map();
    combined.forEach((event, index) => {
      const key = `${event?.timestamp || ""}-${event?.request_id || ""}-${event?.event || index}`;
      unique.set(key, event);
    });
    return [...unique.values()].sort((a, b) => String(b?.timestamp || "").localeCompare(String(a?.timestamp || "")));
  }, [data]);

  const createClient = useCallback(async (client) => {
     const created = await cockpitApi.createClient(client);
    await refreshAll();
    return created;
  }, [refreshAll]);

  return { data, loading, logs, refreshAll, createClient };
}

