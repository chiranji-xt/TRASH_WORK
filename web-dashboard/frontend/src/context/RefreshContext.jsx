import { createContext, useContext, useEffect, useRef, useState } from "react";

const RefreshContext = createContext(0);

export function RefreshProvider({ intervalMs = 30000, children }) {
  const [tick, setTick] = useState(0);
  const timerRef = useRef(null);

  useEffect(() => {
    // Start global heartbeat
    timerRef.current = setInterval(() => {
      setTick((t) => t + 1);
    }, intervalMs);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [intervalMs]);

  return (
    <RefreshContext.Provider value={tick}>{children}</RefreshContext.Provider>
  );
}

export function useRefresh() {
  return useContext(RefreshContext);
}


